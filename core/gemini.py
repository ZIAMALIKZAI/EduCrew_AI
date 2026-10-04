import os
from crewai import LLM
from core.config import GEMINI_API_KEY, DEFAULT_FAST_MODEL

def get_llm(model_name: str = DEFAULT_FAST_MODEL, temperature: float = 0.4):
    """
    Returns CrewAI's native LLM configured for Google Gemini.
    Translates deprecated 1.5 identifiers to active models.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Please supply it via .env or the UI.")

    os.environ["GEMINI_API_KEY"] = api_key
    os.environ["GOOGLE_API_KEY"] = api_key

    # Clean out extra prefixes
    clean_name = model_name.replace("models/", "").replace("gemini/", "").strip()

    # Automatic fallback for deprecated 1.5 endpoints
    if "1.5" in clean_name or not clean_name:
        clean_name = "gemini-2.5-flash"

    return LLM(
        model=f"gemini/{clean_name}",
        api_key=api_key,
        temperature=temperature
    )
