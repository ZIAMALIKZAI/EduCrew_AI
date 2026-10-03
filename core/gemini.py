import os
from crewai import LLM
from core.config import GEMINI_API_KEY, DEFAULT_FAST_MODEL

def get_llm(model_name: str = DEFAULT_FAST_MODEL, temperature: float = 0.4):
    """
    Returns CrewAI's native LLM configured for Google Gemini.
    Model string must follow the format 'gemini/<model_name>'.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Please supply it via .env or the UI.")

    # Ensure environment variables required by CrewAI and google-genai are set
    os.environ["GEMINI_API_KEY"] = api_key

    clean_name = model_name.replace("gemini/", "")
    crewai_model = f"gemini/{clean_name}"

    return LLM(
        model=crewai_model,
        api_key=api_key,
        temperature=temperature
    )
