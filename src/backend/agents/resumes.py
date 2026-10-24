from backend.schemas.agents import ResumeAgentsResponse
from .prompts import EXTRACT_CANDIDATE_SYSTEM_PROMPT
from .llms import model
from langchain.agents import create_agent
from langchain.messages import HumanMessage

agent = create_agent(
    model=model,
    system_prompt=EXTRACT_CANDIDATE_SYSTEM_PROMPT,
    response_format=ResumeAgentsResponse,
)


async def extract_candidate_info(content: str):
    """识别文字"""
    res = await agent.ainvoke(
        {
            "messages": [
                HumanMessage(
                    f"原始文本内容为{content}， 请从原始文本中提取候选人信息成JSON格式"
                )
            ]
        }
    )
    # print(res)
    return res["structured_response"]
