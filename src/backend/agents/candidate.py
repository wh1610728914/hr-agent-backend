# 候选人的agent
# 拿到候选人和职业信息后，对候选人进行评分，给面试官进行面试安排


from typing import Annotated, List

from backend.settings import settings
from backend.schemas.candidate import CandidateSchema
from backend.schemas.position import PositionSchema
from backend.schemas.user import UserSchema


from .llms import model
from langchain.agents import create_agent, AgentState
from langgraph.graph.message import BaseMessage
from langchain.agents.middleware import SummarizationMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

CANDIDATE_PROCESS_SYSTEM_PROMPT = """
你是一个非常专业的HR招聘小助手，会严格按照以下步骤来招聘候选人：
1. 我会把候选人和职位信息发送给你，你首先要给这个候选人进行评分。
2. 如果候选人整体得分超过8分，那么这个候选人就合适，要给这个候选人发送邮件确定面试时间。如果得分低于8分，那么就不予考虑。

3. 但是如果该候选人状态被人工修改为AI筛选通过，并且还没有确定面试时间，那么你还是要发送邮件跟这个候选人确定面试时间。

4. 发送完邮件后，你就可以退出了。直到我把候选人的邮件回复内容发给你，你再决定下一步操作。
5. 如果候选人回复内容为“确定”面试时间，那么你就可以确定面试时间了，整个任务你就完成了。
6. 但是如果候选人回复了新的面试时间，那么你要先判断面试官在该时间内是否空闲，如果空闲，那么就可以确定面试时间了。
7. 如果候选人回复的新的面试时间，面试官不空闲，那么你要告诉候选人，面试官在该时间内不空闲，请候选人重新选择面试时间。
8. 重复5、6、7步骤，直到和候选人确定了面试时间，或者候选人明确拒绝了面试，整个任务就结束了。
8. 如果候选人回复的邮件中包含“拒绝”，那么你要修改候选人的状态为拒绝，整个任务你就完成了。

工具描述：
- get_current_time：如果涉及到相对时间时，比如昨天、明天、后天、下周三等，那么要先调用这个工具获取当前时间，再推测目标时间。
- score_for_candidate：给候选人进行评分。
- get_interviewer_available_slot：获取面试官的空闲时间。
- send_interview_email：给候选人发送邮件，邀请候选人面试。
- confirm_interview_time：如果候选人同意了面试时间，那么调用该工具来确定面试时间。
- refuse_interview：如果候选人拒绝了面试，那么调用该工具来更新候选人状态为已拒绝。
调用了工具后，务必等到工具执行完成后再停止运行。

其他：
- 如果收到和确定面试时间无关的邮件，不予以理会。
"""

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
            tools=[],
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
            state_schema=CandidateAgentState,
        )
        config = {"configurable": {"thread_id": thread_id}}
        await agent.ainvoke({"messages": messages}, config=config)

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
