import os
from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import GEMINI_API_KEY, DEFAULT_FAST_MODEL

def get_llm(model_name: str = DEFAULT_FAST_MODEL, temperature: float = 0.5):
    api_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Please supply it via .env or the UI.")

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=temperature
    )
