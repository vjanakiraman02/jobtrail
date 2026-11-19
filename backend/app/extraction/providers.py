"""Model backends. One OpenAI-compatible client covers both OpenAI and Ollama,
because Ollama exposes the same /v1/chat/completions API."""

from typing import Protocol


class ProviderError(Exception):
    """The model backend could not be reached or gave an unusable response."""


class LLMProvider(Protocol):
    def complete_json(self, *, system: str, user: str) -> str:
        """Return the model's raw reply, which should be a single JSON object."""
        ...


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        # Imported here so the API still starts if the package is missing;
        # only extraction is affected.
        try:
            from openai import OpenAI
        except ImportError as error:
            raise ProviderError(
                "The 'openai' package is not installed. Re-run the backend setup task."
            ) from error
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self._model = model

    def complete_json(self, *, system: str, user: str) -> str:
        from openai import BadRequestError, OpenAIError

        request = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        try:
            try:
                response = self._client.chat.completions.create(temperature=0, **request)
            except BadRequestError as error:
                # Some models only accept the default temperature.
                if "temperature" not in str(error).lower():
                    raise
                response = self._client.chat.completions.create(**request)
        except OpenAIError as error:
            raise ProviderError(f"{type(error).__name__}: {str(error)[:300]}") from error

        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise ProviderError("The model returned an empty reply.")
        return content
