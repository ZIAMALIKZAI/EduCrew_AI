import os
from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import GEMINI_API_KEY, DEFAULT_FAST_MODEL

def get_llm(model_name: str = DEFAULT_FAST_MODEL, temperature: float = 0.5):
    """
    Returns an initialized LangChain ChatGoogleGenerativeAI instance
    configured with request timeouts and exponential backoff retries
    to survive Google API 503 spikes.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Please supply it via .env or the Streamlit sidebar.")

    # max_retries ensures transient 503 high-demand errors are retried automatically
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=temperature,
        max_retries=6,
        timeout=120
    )
