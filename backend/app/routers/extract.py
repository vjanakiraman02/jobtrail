import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.config import settings
from app.extraction.factory import ProviderConfigError, build_provider
from app.extraction.providers import LLMProvider, ProviderError
from app.extraction.schema import ExtractedJob
from app.extraction.service import ExtractionError, extract_job

logger = logging.getLogger("jobtrail.extraction")

router = APIRouter(prefix="/api/v1", tags=["extraction"])


class ExtractRequest(BaseModel):
    text: str = Field(min_length=20, max_length=50_000)


def get_provider() -> LLMProvider:
    try:
        return build_provider(settings)
    except ProviderConfigError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error
    except ProviderError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error


@router.post("/extract", response_model=ExtractedJob)
def extract(payload: ExtractRequest, provider: Annotated[LLMProvider, Depends(get_provider)]):
    """Pull structured fields out of pasted posting text. Nothing is saved."""
    try:
        return extract_job(payload.text, provider)
    except ProviderError as error:
        # Never log the posting text itself, only the error.
        logger.warning("model request failed: %s", error)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"The model request failed ({error}). "
            "Check your LLM settings and that the model is running.",
        ) from error
    except ExtractionError as error:
        logger.warning("extraction failed: %s", error)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "The model's answer could not be understood. "
            "Try again, or fill in the details by hand.",
        ) from error
