# 候选人的agent
# 拿到候选人和职业信息后，对候选人进行评分，给面试官进行面试安排


from datetime import datetime, timedelta
from typing import Annotated, List
from zoneinfo import ZoneInfo

from backend.core.cache import HRCache
from backend.core.dingtalk import DingTalkApi, DingTalkHttp
from backend.core.emailBot.bot import EmailBot
from backend.core.exceptions import BusinessException
from backend.db.database import SessionLocal
from backend.dependencies.user import get_cache_instance
from backend.core.emailBot.settings import EmailBotSetting
from backend.models.candidate import CandidateStatusEnum
from backend.models.interview import InterviewResultEnum
from backend.repository.candidate import CandidateRepo
from backend.repository.interview import Interview
from backend.repository.user import UserRepo
from backend.settings import settings
from backend.schemas.candidate import CandidateSchema
from backend.schemas.position import PositionSchema
from backend.schemas.user import DingUserResponse, UserSchema
from backend.utils.datetime import iso_to_dt
from backend.utils.datetime import find_free_slot, get_future_time
from backend.utils.datetime import dt_to_iso
import httpx
from langgraph.prebuilt import ToolRuntime
from loguru import logger
from sqlalchemy.exc import IntegrityError
from langgraph.errors import GraphRecursionError

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
from langchain.messages import HumanMessage, AIMessage
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
    """给候选人进行评分
    评分结果会存入数据库中，并根据评分结果修改候选人状态。
        return：
        - str | None: 评分结果的JSON字符串，如果评分失败则返回None
    """
    agent = _score_agent
    state = runtime.state
    candidate = state["candidate"]
    position = state["position"]
    if not candidate or not position:
        return "缺少候选人或者职位信息"

    try:
        # 解析SCORE_FOR_CANDIDATE_USER_PROMPT里面的变量 用PromptTemplate
        user_prompt_template = PromptTemplate.from_template(
            SCORE_FOR_CANDIDATE_USER_PROMPT
        )
        # invoke 可以把传入的json
        user_prompt = user_prompt_template.invoke(
            {
                "candidate": candidate.model_dump_json(),
                "position": position.model_dump_json(),
            }
        )

        res = await agent.ainvoke(
            {"messages": [HumanMessage(content=user_prompt.text)]}
        )

        candidate_scope: CandidateAIScopeSchema = res["structured_response"]
        candidate_id = candidate.id
        # 插到数据库里面，连数据库，手动连
        try:
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
                            candidate_id,
                            CandidateStatusEnum.AI_FILTER_PASSED,
                        )
                    else:
                        await candidate_Repo.update_candidate_status(
                            candidate_id, CandidateStatusEnum.AI_FILTER_FAILED
                        )
        except Exception as e:
            logger.exception(f"更改候选人状态失败，严重错误: {e}")
            return (
                f"【系统严重错误】更改候选人状态失败。"
                f"**请立即中断对话，严禁调用任何工具，直接向HR输出：'数据库写入失败，流程已中断，请人工处理。'**"
            )

        return f"得分工具执行成功，该候选人得分为:{candidate_scope.model_dump_json()}"
    except Exception as e:
        logger.exception(f"打分系统发生严重异常: {e}")
        return f"【系统错误】得分工具执行失败，错误：{e}。**请立即终止所有流程，严禁重试，直接向HR报告此错误。**"


@tool
async def get_interviewer_available_slot(runtime: ToolRuntime[CandidateAgentState]):
    """获取面试官空余时间"""
    # 1.拿到面试官数据和钉钉数据
    interview = runtime.state["interview"]

    union_id: str | None = None
    http_client = DingTalkHttp()
    # 1.获取钉钉账户
    try:

        async with SessionLocal() as db:
            async with db.begin():
                user_Repo = UserRepo(db)
                ding_user_info: DingUserResponse = await user_Repo.get_ding_info_repo(
                    interview.id
                )
                if not ding_user_info:
                    return (
                        f"无该面试官{interview.username}的钉钉信息"
                        f"**无法安排面试，请立即终止所有操作，通知HR绑定钉钉。**"
                    )
                union_id = ding_user_info.union_id
    except Exception as e:
        logger.exception(f"查询面试官钉钉信息失败，错误是{e}")
        return (
            f"【系统严重错误】查询面试官钉钉信息失败。"
            f"**请立即中断对话，严禁调用任何工具，直接向HR输出：'数据库查询面试官钉钉信息失败，流程已中断，请人工处理。'**"
        )
    # 2.获取钉钉日程视图
    # try:
    # except Exception as e:
    #         logger.exception(f"获取钉钉日程列表失败，错误是{e}")
    #         return (
    #             f"获取钉钉日程列表失败",
    #             f"**请立即中断对话，严禁调用任何工具，直接向HR输出：'获取钉钉日程列表失败失败，流程已中断，请人工处理。'**",
    #         )
    ding_calendar_url = DingTalkApi.get_calendar_url(union_id)
    timeMin = get_future_time(hour=9)  # 返回的iso
    timeMax = get_future_time(hour=9, days=7)  # 返回的iso
    cache: HRCache = get_cache_instance()
    raw = await cache.get_ding_info(user_id=interview.id)
    if not raw:
        return f"面试官{interview.username}的钉钉token不存在或已过期"

    calendar_resp = {}

    async def fetch_calendar(access_token: str):
        """封装起来，方便重试"""
        async with httpx.AsyncClient(timeout=10) as client:
            return await client.get(
                url=ding_calendar_url,
                params={
                    "timeMin": timeMin,
                    "timeMax": timeMax,
                },
                headers={"x-acs-dingtalk-access-token": access_token},
            )

    try:
        resp = await http_client.request_with_ding_token(
            user_id=interview.id, make_request=fetch_calendar
        )
        resp.raise_for_status()
        calendar_resp = resp.json()

    except Exception as e:
        logger.exception(f"获取钉钉日程列表失败，错误是{e}")
        return (
            f"获取钉钉日程列表失败"
            f"**请立即中断对话，严禁调用任何工具，直接向HR输出：'获取钉钉日程列表失败失败，流程已中断，请人工处理。'**"
        )
    # 3.解析并获取空闲时间
    events = calendar_resp.get("events") or []
    dt_time_max = iso_to_dt(timeMax)
    dt_time_min = iso_to_dt(timeMin)
    if not events:
        return f"该时段【{dt_time_min:%Y-%m-%d %H:%M} - {dt_time_max:%Y-%m-%d %H:%M}】时间全部空闲"
    events_list = []
    for event in events:
        s = event["start"].get("dateTime") or event["start"].get("date")
        e = event["end"].get("dateTime") or event["end"].get("date")
        events_list.append((iso_to_dt(s), iso_to_dt(e)))

    try:
        free_slot = find_free_slot(
            start_time=dt_time_min, end_time=dt_time_max, existing_events=events_list
        )
    except Exception as e:
        logger.exception(f"查找空闲时间段失败，内部报错: {e}")
        return (
            f"查找空闲时间段失败，系统内部错误：{e}。"
            f"**请立即中断对话，严禁调用任何工具，直接向HR输出：'空闲时间计算失败，无法安排面试，请人工介入。'**"
        )
    if free_slot:
        s, e = free_slot
        return f"找到空闲时间了：{s:%Y-%m-%d %H:%M} - {e:%Y-%m-%d %H:%M}"
    return f"没有空闲时间"


@tool
async def confirm_interview_time(
    interview_datetime_str: str, runtime: ToolRuntime[CandidateAgentState]
):
    """
    确定面试时间
    参数：
        interview_datetime_str：面试时间，传来的是 ISO8601格式的字符串

    给候选人发送面试安排邮件
    在面试官的钉钉上添加一条面试日程
    在系统上添加一条待面试的记录
    更改候选人的状态为待面试
    """
    try:
        interview_datetime: datetime = iso_to_dt(interview_datetime_str)
        # 由于后面存储数据库，不能在日期中带时区，所以这里先处理一下
        if interview_datetime.tzinfo is not None:
            interview_datetime_without_tz = interview_datetime.astimezone(None).replace(
                tzinfo=None
            )
    except Exception as e:
        return f"{interview_datetime_str}格式化失败！{e}"

    candidate: CandidateSchema = runtime.state["candidate"]
    position: PositionSchema = runtime.state["position"]
    user: UserSchema = runtime.state["interview"]
    results = []
    # 1.给候选人发送面试安排邮件
    body = f"""
            您好！经过初步沟通，现向您发送最终的面试确认信息：
            面试岗位：{position.title}
            面试时间：{interview_datetime}
            面试方式：线下面试
            预计时长：30分钟

            请您提前安排好时间准时参加。此信息为最终确认通知，无需回复。
            祝好！"""
    botObj = EmailBotSetting(
        imap_host=settings.IMAP_HOST,
        smtp_host=settings.SMTP_HOST,
        email=settings.EMAIL_USERNAME,
        password=settings.EMAIL_PASSWORD,
    )
    to = candidate.email
    subject = "美味黄油【面试邀请】"
    try:
        async with EmailBot(botObj) as bot:
            await bot.send_email(to=to, subject=subject, text=body)
        results.append("最终确认面试邮件发送成功")
    except Exception as e:
        results.append(f"最终确认面试邮件发送失败，错误是：{e}")
        logger.error(f"发送确认邮件给候选人 {candidate.name} 失败: {e}")
        return (
            f"最终确认面试邮件发送失败"
            f"系统错误：最终确认面试邮件发送失败。**请立即终止流程，向HR报告此代码错误。严禁重试！**",
        )
    # 2.在面试官的钉钉上添加一条面试日程
    union_id: str | None = None

    try:
        async with SessionLocal() as db:
            async with db.begin():
                user_repo = UserRepo(db)
                user_ding_info: DingUserResponse = await user_repo.get_ding_info_repo(
                    user_id=user.id
                )
                if not user_ding_info:
                    results.append("面试官未绑定钉钉，日程创建失败。")
                    return "无面试官钉钉信息"
                union_id = user_ding_info.union_id
        url = DingTalkApi.create_calendar_url(unionID=union_id)

        start_dt = (
            iso_to_dt(interview_datetime)
            if isinstance(interview_datetime, str)
            else interview_datetime
        )
        data = {
            "summary": "面试安排",
            "start": {
                "dateTime": dt_to_iso(start_dt),
            },
            "end": {
                "dateTime": dt_to_iso(start_dt + timedelta(minutes=30)),
            },
        }

        async def create_calendar(access_token: str):
            async with httpx.AsyncClient(timeout=10) as client:
                return await client.post(
                    url=url,
                    json=data,
                    headers={"x-acs-dingtalk-access-token": access_token},
                )

        try:
            http_client = DingTalkHttp()
            resp = await http_client.request_with_ding_token(user.id, create_calendar)
            if resp.status_code != 200:
                results.append(
                    f"钉钉接口添加面试日程错误，错误码是:{resp.status_code},错误是:{resp.text}"
                )
            else:
                results.append("钉钉创建面试日程成功")

        except BusinessException as e:
            results.append(f"钉钉创建面试日程失败：{e}")

    except Exception as e:
        results.append(f"钉钉创建面试日程失败,错误是{e}")

    # 3.在系统上添加一条待面试的记录
    try:
        async with SessionLocal() as db:
            async with db.begin():
                Interview_repo = Interview(db)
                # 数据库只能添加datetime的
                await Interview_repo.create_interview_repo(
                    {
                        # 面试时间因为是存储到postgresql数据库中，现在是只能存储没有带时区的日期
                        "scheduled_time": interview_datetime_without_tz,
                        "result": InterviewResultEnum.PENDING,
                        "candidate_id": candidate.id,
                        "interviewer_id": user.id,
                    }
                )

                # 4.更改候选人的状态为待面试
                candidate_repo = CandidateRepo(db)
                res = await candidate_repo.update_candidate_status(
                    id=candidate.id, val=CandidateStatusEnum.WAITING_FOR_INTERVIEW
                )
                if not res:
                    return "更新候选人状态失败，未找到该候选人"

        results.append("系统记录创建成功，候选人状态已更新")
    except IntegrityError:
        return f"该候选人已安排过面试，请勿重复操作,请直接结束当前流程。"

    except Exception as e:
        return f"【系统严重错误】安排面试数据库写入失败：{e}。**请立即中断对话，严禁调用任何工具，直接向HR输出：'数据库写入失败，流程已中断，请人工处理。'**"

    final_report = "面试安排流程执行完毕，详情如下：\n" + "\n".join(
        [f"- {r}" for r in results]
    )
    return final_report


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
    if candidate.status == CandidateStatusEnum.WAITING_FOR_INTERVIEW:
        return "候选人已处于待面试状态，无需再次发送邀约邮件。"
    text = f"""
                您好！感谢您对我们{position.title}岗位的关注。经初步沟通，我们诚挚邀请您参加面试：
                    面试时间：{interview_datetime}
                    面试方式：线下面试
                    预计时长：30分钟
                    如上述时间与您安排有冲突，请随时回复本消息告知我，我们可以为您协调其他合适的时间，无需勉强。
                    期待您的回复，祝好！
            """
    async with EmailBot(botObj) as bot:
        to = candidate.email
        subject = "美味黄油【面试邀请】"

        try:
            await bot.send_email(to=to, subject=subject, text=text)
            return (
                f"给候选人发送面试邮件成功！面试时间初步确认为:{interview_datetime}。"
                f"**【重要指令】邀约邮件已发送，当前任务已彻底完成！请立即结束对话，严禁再调用任何工具！等待候选人回复即可。**"
            )
        except Exception as e:
            logger.warning(e)
            return f"发送邮件失败：{e}。这是一个系统错误，请立即终止当前任务，不要再尝试发送邮件，向HR报告错误。"


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
        return f"拒绝面试状态更新失败，错误: {e}。**请立即终止操作，直接向HR报告。**"


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
            tools=[
                get_current_time,
                score_for_candidate,
                send_interview_email,
                get_interviewer_available_slot,
                refuse_interview,
                confirm_interview_time,
            ],
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
        config = {
            "configurable": {"thread_id": thread_id},
            # 限制最大循环次数
            "recursion_limit": 30,
        }
        try:
            async for event in agent.astream(
                {
                    "messages": messages,
                    "candidate": self.candiadate,
                    "position": self.position,
                    "interview": self.interview,
                },
                config=config,
            ):
                for node_name, state in event.items():
                    logger.info(f"--- 节点: {node_name} ---")
                    if state and isinstance(state, dict) and "messages" in state:
                        final_state = state  # 保存最新状态
                        msg = state["messages"][-1]
                        logger.info(f"类型: {msg.type} | 内容: {msg.content}")

                        # 🚨 终极刹车：如果你发现工具成功发完邮件了
                        if msg.type == "tool" and "发送面试邮件成功" in msg.content:
                            logger.info("✅ 邮件发送成功，强行终止 Agent 循环！")
                            # 手动追加一条 AI 的回复，让最终结果完整
                            state["messages"].append(
                                AIMessage(
                                    content="已成功发送初试邀约邮件，等待候选人回复。"
                                )
                            )
                            return state  # 👈 直接 return，打破循环！

            return final_state
        except GraphRecursionError:
            logger.warning("Agent 达到递归上限，返回已有状态")
            return (
                final_state
                if final_state
                else {"messages": [AIMessage(content="流程执行步数超限，请人工检查。")]}
            )
        except Exception as e:
            logger.error(f"❌ 执行崩溃: {e}")
            raise e

        return result

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
