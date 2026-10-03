import os
from crewai import LLM
from core.config import GEMINI_API_KEY, DEFAULT_FAST_MODEL

def get_llm(model_name: str = DEFAULT_FAST_MODEL, temperature: float = 0.5):
    """
    Returns CrewAI's native LLM wrapper configured for Google Gemini.
    Model names format for CrewAI: 'gemini/gemini-1.5-flash'
    """
    api_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Please supply it via .env or the Streamlit sidebar.")

    # CrewAI requires provider prefix 'gemini/'
    formatted_model = model_name if model_name.startswith("gemini/") else f"gemini/{model_name}"

    return LLM(
        model=formatted_model,
        api_key=api_key,
        temperature=temperature
    )
