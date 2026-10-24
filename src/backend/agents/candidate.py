# 候选人的agent
# 拿到候选人和职业信息后，对候选人进行评分，给面试官进行面试安排


from typing import Annotated, List

from backend.core.exceptions import BusinessException
from backend.db.database import SessionLocal
from backend.models.candidate import CandidateStatusEnum
from backend.repository.candidate import CandidateRepo
from backend.settings import settings
from backend.schemas.candidate import CandidateSchema
from backend.schemas.position import PositionSchema
from backend.schemas.user import UserSchema
from langgraph.prebuilt import ToolRuntime


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
        raise BusinessException(message="缺少候选人或者职位信息")
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
            try:
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
            except Exception as e:
                return f"得分工具执行失败，错误：{e}"

    return f"得分工具执行成功，该候选人得分为:{candidate_scope.model_dump_json()}"


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
            tools=[score_for_candidate],
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
