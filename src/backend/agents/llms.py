# 这里放置 存放大模型连接的对象
import os
from backend.settings import settings
from langchain_openai import ChatOpenAI

api_key = os.getenv("DASHSCOPE_API_KEY")

# ChatOpenAI 特有的模型类
qwen_llm = ChatOpenAI(
    model=settings.LLM_QIAN_MODEL, base_url=settings.LLM_URL, api_key=api_key
)

# deepseek_llm = ChatOpenAI(
#     model=settings.LLM_DEEPSEEK_MODEL, base_url=settings.LLM_URL, api_key=api_key
# )
