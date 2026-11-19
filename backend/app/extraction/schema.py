"""The shape of what the model must return, plus forgiving normalization.

Models are inconsistent about blanks ("N/A", "Not specified") and spelling
("On-site", "Remote"), so the validators clean those up before strict checks.
"""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

WorkMode = Literal["onsite", "hybrid", "remote"]

_BLANK_WORDS = {"", "n/a", "na", "none", "null", "unknown", "not specified", "not stated", "-"}
_WORK_MODE_ALIASES = {
    "onsite": "onsite",
    "on-site": "onsite",
    "on site": "onsite",
    "in-office": "onsite",
    "in office": "onsite",
    "in person": "onsite",
    "hybrid": "hybrid",
    "remote": "remote",
    "fully remote": "remote",
    "work from home": "remote",
}

MAX_FIELD_CHARS = 200  # matches the Application table's column limits
MAX_SKILLS = 30
MAX_SKILL_CHARS = 60


class ExtractedJob(BaseModel):
    company: str | None = None
    title: str | None = None
    location: str | None = None
    work_mode: WorkMode | None = None
    salary_range: str | None = None
    required_skills: list[str] = Field(default_factory=list)

    @field_validator("company", "title", "location", "salary_range", mode="before")
    @classmethod
    def _clean_text(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("must be a string or null")
        value = value.strip()
        if value.casefold() in _BLANK_WORDS:
            return None
        return value[:MAX_FIELD_CHARS]

    @field_validator("work_mode", mode="before")
    @classmethod
    def _clean_work_mode(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("must be a string or null")
        # An unrecognised value becomes null rather than failing the whole extraction.
        return _WORK_MODE_ALIASES.get(re.sub(r"\s+", " ", value.strip().casefold()))

    @field_validator("required_skills", mode="before")
    @classmethod
    def _clean_skills(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("must be a list of strings")
        seen: set[str] = set()
        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("every skill must be a string")
            skill = item.strip()
            key = skill.casefold()
            if not skill or len(skill) > MAX_SKILL_CHARS or key in seen:
                continue
            seen.add(key)
            cleaned.append(skill)
        return cleaned[:MAX_SKILLS]
