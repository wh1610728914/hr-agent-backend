from backend.schemas.agents import ResumeAgentsResponse

from .llms import model
from langchain.agents import create_agent
from langchain.messages import HumanMessage

# 提示词
EXTRACT_CANDIDATE_SYSTEM_PROMPT = """
你是一位经验丰富的人力资源（HR）专家，擅长从杂乱、无序的内容中精准、高效地提取关键信息。
你的任务是仔细分析提供的简历文本，并将其结构化为JSON格式。
1. **灵活性与准确性**：简历的表述可能不尽相同，例如“工作经验”可能被称为“工作经历”。请理解上下文，准确提取信息。
2. **处理噪声**：从文件转换的文本可能包含格式错误或无关字符，请忽略这些噪声，专注于提取有效信息。
3. **生日**：如果原始文本中只包含年份，那么就将日期设置为01月01日。
"""


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
