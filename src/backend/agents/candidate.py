# 候选人的agent
# 拿到候选人和职业信息后，对候选人进行评分，给面试官进行面试安排


from datetime import datetime
from typing import Annotated, List
from zoneinfo import ZoneInfo

from backend.core.dingtalk import DingTalkApi
from backend.core.emailBot.bot import EmailBot
from backend.core.exceptions import BusinessException
from backend.db.database import SessionLocal
from backend.dependencies.user import get_cache_instance
from backend.emailBot.settings import EmailBotSetting
from backend.models.candidate import CandidateStatusEnum
from backend.models.ding import DingDingModel
from backend.repository.candidate import CandidateRepo
from backend.repository.user import UserRepo
from backend.schemas.cache import DingTalkTokenInfoSchema
from backend.settings import settings
from backend.schemas.candidate import CandidateSchema
from backend.schemas.position import PositionSchema
from backend.schemas.user import UserSchema
from backend.utils.date import iso_to_dt
from backend.utils.datetime import find_free_slot, get_future_time
from backend.utils.datetime import dt_to_iso
import httpx
from langgraph.prebuilt import ToolRuntime
from loguru import logger


from .llms import model
from langchain.agents import create_agent, AgentState
from langgraph.graph.message import BaseMessage
from langchain.agents.middleware import SummarizationMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from .prompts import (
    CANDIDATE_PROCESS_SYSTEM_PROMPT,
    SCORE_FOR_CANDIDATE_SYSTEM_PROMPT,
    SCORE_FOR_CANDIDATE_USER_PROMPT,
)
from langchain.tools import tool
from backend.schemas.candidate import CandidateAIScopeSchema
from langchain.messages import HumanMessage
from langchain_core.prompts import PromptTemplate


# 候选人 -》 ai评分 -》 评分 大于 8分 -》 llm发邮件 ->邀请面试预约
#                                                  此刻在面试表中插入一条预约记录 -》 给面试官在钉钉上发面试安排
# 给大模型传 候选人和职位信息
def keep_old(left, right):
    """有就用新值，没有就用旧值"""
    return right if right is not None else left


class CandidateAgentState(AgentState):
    # 执行的流程中，只有第一次才传所有的候选人信息，那之后的话，候选人信息不传了，那就用之前的
    candidate: Annotated[CandidateSchema, keep_old] = None
    position: Annotated[PositionSchema, keep_old] = None
    interview: Annotated[UserSchema, keep_old] = None


_score_agent = create_agent(
    model=model,
    system_prompt=SCORE_FOR_CANDIDATE_SYSTEM_PROMPT,
    response_format=CandidateAIScopeSchema,
)


# 工具
@tool
async def score_for_candidate(runtime: ToolRuntime[CandidateAgentState]):
    """给候选人进行评分"""
    agent = _score_agent
    state = runtime.state
    candidate = state["candidate"]
    position = state["position"]
    if not candidate or not position:
        return "缺少候选人或者职位信息"

    try:
        # 解析SCORE_FOR_CANDIDATE_USER_PROMPT里面的变量 用PromptTemplate
        user_prompt_template = PromptTemplate(SCORE_FOR_CANDIDATE_USER_PROMPT)
        # invoke 可以把传入的json
        user_prompt = user_prompt_template.invoke(
            {
                "candidate": candidate.model_dump_json(),
                "position": position.model_dump_json(),
            }
        )
        res = await agent.ainvoke({"messages": [HumanMessage(content=user_prompt)]})
        candidate_scope: CandidateAIScopeSchema = res["structured_response"]
        candidate_id = candidate.id
        # 插到数据库里面，连数据库，手动连
        async with SessionLocal() as db:
            async with db.begin():
                candidate_Repo = CandidateRepo(db)
                await candidate_Repo.create_ai_scope(
                    candidate_id=candidate_id,
                    candidate_scope_dict=candidate_scope.model_dump(),
                )
                # 判断overall_score得分情况，大于8分的，修改状态为AI_FILTER_PASSED 否则 AI_FILTER_FAILED
                if candidate_scope.overall_score > 8:
                    await candidate_Repo.update_candidate_status(
                        candidate_id, CandidateStatusEnum.AI_FILTER_PASSED
                    )
                else:
                    await candidate_Repo.update_candidate_status(
                        candidate_id, CandidateStatusEnum.AI_FILTER_FAILED
                    )
        return f"得分工具执行成功，该候选人得分为:{candidate_scope.model_dump_json()}"
    except Exception as e:
        return f"得分工具执行失败，错误：{e}"


# # 获取钉钉的accesstoken，如果过期的话，用refresh_token进行更新就好！
# async def get_ding_access_token(user_id:str) -> str:
#     """获取钉钉的accesstoken"""


@tool
async def get_interviewer_available_slot(runtime: ToolRuntime[CandidateAgentState]):
    """获取面试官空余时间"""
    # 1.拿到面试官数据和钉钉数据
    interview_id = runtime.state["interview"].id

    union_id: str | None = None

    # 1.获取钉钉账户
    async with SessionLocal() as db:
        async with db.begin():
            try:
                user_repo = UserRepo(db)
                ding_user_info: DingDingModel = user_repo.get_ding_info(interview_id)

                if not ding_user_info:
                    return "获取候选人可用时间失败，该用户没有注册钉钉"
                union_id = ding_user_info.union_id
            except Exception as e:
                return f"获取候选人可用时间失败，错误：{e}"

    # 2.获取钉钉的请求头需要的 access_token
    cache = get_cache_instance()
    ding_tokens: DingTalkTokenInfoSchema = cache.get_ding_info(interview_id)
    if not ding_tokens:
        return "钉钉 access_token 缺失，请重新授权 "
    calendar_url = DingTalkApi.build_calendar_list_url(union_id)
    timeMin = dt_to_iso(get_future_time(9))
    timeMax = dt_to_iso(get_future_time(9, 7))

    async def _fetch_events(access_token: str):
        """返回 (status_code, data)；网络异常直接抛"""
        async with httpx.AsyncClient() as client:
            res = await client.get(
                calendar_url,
                params={"timeMin": timeMin, "timeMax": timeMax},
                headers={"x-acs-dingtalk-access-token": access_token},
            )
            return res

    try:
        res = await _fetch_events(ding_tokens.access_token)
        if res.status_code in (401, 403):
            logger.warning("access_token 失效，尝试刷新 interview_id=%s", interview_id)
            new_refresh_token, new_access_token = (
                await DingTalkApi.refresh_access_token(ding_tokens.refresh_token)
            )
            # 重新写回缓存
            await cache.set_ding_info(
                DingTalkTokenInfoSchema(
                    access_token=new_access_token,
                    refresh_token=new_refresh_token,
                    user_id=interview_id,
                )
            )
            ding_tokens = cache.get_ding_info(user_id=interview_id)
            res = await _fetch_events(new_access_token)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        logger.exception("调用钉钉日历接口失败 interview_id=%s", interview_id)
        return f"获取面试官空余时间失败，钉钉接口错误：{e}"

    # 4.计算空余时间
    events = data.get("events") or []
    if not events:
        return f"该时间段全部空闲：{timeMin} ~ {timeMax}"
    try:

        time_list = [
            (
                iso_to_dt(event["start"]["dateTime"]),
                iso_to_dt(event["end"]["dateTime"]),
            )
            for event in events
        ]
        free_slot = find_free_slot(
            start_time=iso_to_dt(timeMin),
            end_time=iso_to_dt(timeMax),
            existing_events=time_list,
        )
    except Exception as e:
        logger.exception("解析钉钉日历事件失败 interview_id=%s", interview_id)
        return f"解析日历事件失败：{e}"
    if free_slot:
        s, e = free_slot
        return f"找到空余时间了：{s:%Y-%m-%d %H:%M} ~ {e:%Y-%m-%d %H:%M}"

    return f"没有空余时间"


@tool
async def send_interview_email(
    interview_datetime: str, runtime: ToolRuntime[CandidateAgentState]
):
    """给候选人发送面试的邮件
    interview_datetime:面试时间
    """
    botObj = EmailBotSetting(
        imap_host=settings.IMAP_HOST,
        smtp_host=settings.SMTP_HOST,
        email=settings.EMAIL_USERNAME,
        password=settings.EMAIL_PASSWORD,
    )
    state: CandidateAgentState = runtime.state
    candidate = state["candidate"]
    position: PositionSchema = state["position"]
    async with EmailBot(botObj) as bot:
        to = candidate.email
        subject = "美味味道【面试邀请】"
        text = f"""
                您好！感谢您对我们{position.title}岗位的关注。经初步沟通，我们诚挚邀请您参加面试：
                    面试时间：{interview_datetime}
                    面试方式：线下面试
                    预计时长：30分钟
                    如上述时间与您安排有冲突，请随时回复本消息告知我，我们可以为您协调其他合适的时间，无需勉强。
                    期待您的回复，祝好！
            """
        html = f"""
                    您好！感谢您对我们岗位的关注。经初步沟通，我们诚挚邀请您参加面试：<br/>
                    面试时间：{interview_datetime}  <br/>
                    面试方式：线下面试 <br/>
                    预计时长：30分钟 <br/>
                    如上述时间与您安排有冲突，请随时回复本消息告知我，我们可以为您协调其他合适的时间，无需勉强。<br/>
                    期待您的回复，祝好！
        """
        try:
            await bot.send_email(to=to, subject=subject, text=text, html=html)
        except Exception as e:
            logger.warning(e)
            return f"给候选人发送邮件失败:{e}"

        return f"给候选人发送面试邮件成功！面试时间初步确认为:{interview_datetime}"


@tool
async def refuse_interview(runtime: ToolRuntime[CandidateAgentState]):
    """如果候选人拒绝了面试，那么调用该工具来更新候选人状态为已拒绝"""
    candidate: CandidateSchema = runtime.state["candidate"]
    try:
        async with SessionLocal() as db:
            async with db.begin():
                candidate_repo = CandidateRepo(db)

                await candidate_repo.update_candidate_status(
                    candidate.id, CandidateStatusEnum.REFUSED_INTERVIEW
                )
        return f"已成功将候选人状态更新为：已拒绝面试"
    except Exception as e:
        return f"调用拒绝面试工具失败，错误是:{e}"


@tool
async def get_current_time():
    """获取当前时间：年月日，时分秒，星期几，当前第几天"""
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekdays[now.weekday()]
    day = now.day

    return (
        f"{now.year}年{now.month}月{now.day}日"
        f"{now.hour:02d}{now.minute:02d}{now.second:02d}"
        f"{weekday}(本月第{day}天)"
    )


# 此agent 要评分，判断，发邮件，插入面试邀请，给面试管发送信息
class CandidateProcessAgent:

    # 给候选人打分！那得获取到候选人信息和职位信息,
    # 如果简历不错，还要给面试官发送已预约的面试安排 --》 面试官的信息
    def __init__(
        self,
        candidateInfo: CandidateSchema | None = None,
        positionInfo: PositionSchema | None = None,
        interviewInfo: UserSchema | None = None,
    ):
        self.candiadate = candidateInfo
        self.position = positionInfo
        self.interview = interviewInfo
        self._checkpointer = None

    # 通过邮件协商面试时间的话，通过邮件沟通 --》 定时器，读取邮件，发给llm
    async def ainvoke(self, thread_id: str, messages: List[BaseMessage]):
        agent = create_agent(
            model=model,
            tools=[score_for_candidate, send_interview_email],
            system_prompt=CANDIDATE_PROCESS_SYSTEM_PROMPT,
            middleware=[
                SummarizationMiddleware(
                    model=model,
                    trigger=("tokens", 50000),
                    # 不管怎么总结，最近2条消息要保留
                    keep=("messages", 2),
                )
            ],
            checkpointer=self._checkpointer,
            #
            state_schema=CandidateAgentState,
        )
        config = {"configurable": {"thread_id": thread_id}}
        await agent.ainvoke(
            {
                "messages": messages,
                "candidate": self.candiadate,
                "position": self.position,
                "interview": self.interview,
            },
            config=config,
        )

    # 要想变成 异步上下文管理的话，就得加下面两个方法
    async def __aenter__(self):
        """当with的时候，进来的方法"""
        self._checkpointer_conn = AsyncPostgresSaver.from_conn_string(
            settings.DATABASE_AGENT_URL
        )
        # 手动执行__aenter__方法，手动连数据库
        self._checkpointer = await self._checkpointer_conn.__aenter__()
        # 必须写，自动建表
        await self._checkpointer.setup()
        return self  # 必须要return self ，这样如果要创建直接 xxx.checkpointer就可以了

    async def __aexit__(self, exc_type, exc, tb):
        """当离开的时候，出去的方法"""
        print("连接关闭", exc_type, exc, tb)
        await self._checkpointer_conn.__aexit__(exc_type, exc, tb)
