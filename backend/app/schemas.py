from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import Status


def _check_url(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if not value.startswith(("http://", "https://")):
        raise ValueError("url must start with http:// or https://")
    return value


class ApplicationBase(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    url: str | None = Field(default=None, max_length=2000)
    status: Status = Status.saved
    description: str | None = None
    notes: str | None = None
    applied_on: date | None = None

    _validate_url = field_validator("url")(_check_url)


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    """Partial update: only fields that are sent are changed."""

    company: str | None = Field(default=None, min_length=1, max_length=200)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    url: str | None = Field(default=None, max_length=2000)
    status: Status | None = None
    description: str | None = None
    notes: str | None = None
    applied_on: date | None = None

    _validate_url = field_validator("url")(_check_url)

    @field_validator("company", "title", "status")
    @classmethod
    def _not_null(cls, value):
        if value is None:
            raise ValueError("this field cannot be null")
        return value


class ApplicationRead(ApplicationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
