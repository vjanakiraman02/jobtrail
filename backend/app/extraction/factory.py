from app.config import Settings
from app.extraction.providers import LLMProvider, OpenAICompatibleProvider

OLLAMA_DEFAULT_URL = "http://localhost:11434/v1"


class ProviderConfigError(Exception):
    """LLM settings are missing or incomplete. The message says what to set."""


def build_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "none":
        raise ProviderConfigError(
            "AI extraction is turned off. Set LLM_PROVIDER to 'ollama' or 'openai' in .env "
            "(see the README), then restart the API."
        )
    if not settings.llm_model:
        raise ProviderConfigError("Set LLM_MODEL in .env (the model name your provider uses).")

    if settings.llm_provider == "ollama":
        return OpenAICompatibleProvider(
            model=settings.llm_model,
            api_key="ollama",  # Ollama ignores the key, but the client requires one.
            base_url=settings.llm_base_url or OLLAMA_DEFAULT_URL,
            timeout=settings.llm_timeout_seconds,
        )

    api_key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else ""
    if not api_key:
        raise ProviderConfigError("Set LLM_API_KEY in .env to use the OpenAI provider.")
    return OpenAICompatibleProvider(
        model=settings.llm_model,
        api_key=api_key,
        base_url=settings.llm_base_url or None,
        timeout=settings.llm_timeout_seconds,
    )
