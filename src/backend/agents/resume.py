# 跟简历相关的智能体
from backend.schemas.agents import ResumeAgentsResponse
from langchain.agents import create_agent
from loguru import logger
from .llms import qwen_llm
from langchain.agents.middleware import ModelFallbackMiddleware
from .prompts import EXTRACT_CANDIDATE_SYSTEM_PROMPT

# create_agent 创建智能体
agent = create_agent(
    model=qwen_llm,
    #  当主模型不能用的时候切换到备用模型
    # middleware=[ModelFallbackMiddleware(first_model=deepseek_llm)],
    system_prompt=EXTRACT_CANDIDATE_SYSTEM_PROMPT,
    # response_format 结构化输出，要求返回的格式
    response_format=ResumeAgentsResponse,
)


async def extract_candidate_info(content: str) -> ResumeAgentsResponse:
    # 异步调用大模型
    res = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"原始文本内容为{content}， 请从原始文本中提取候选人信息成JSON格式",
                }
            ]
        }
    )
    logger.info("大模型", res)
    return res["structured_response"]
