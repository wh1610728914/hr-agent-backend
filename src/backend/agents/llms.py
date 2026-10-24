import os

from backend.settings import settings
from langchain_openai import ChatOpenAI

key = os.getenv("DASHSCOPE_API_KEY")
model = ChatOpenAI(
    model=settings.LLM_QIAN_MODEL, base_url=settings.LLM_URL, api_key=key
)
