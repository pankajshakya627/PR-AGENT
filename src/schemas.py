from typing import List
from pydantic import BaseModel, Field, field_validator

ALLOWED_CHANGELOG_TYPES = {"feat", "fix", "chore", "docs", "refactor", "performance", "security"}

class ChangelogEntry(BaseModel):
    type: str = Field(description="e.g. feat, fix, chore, docs, refactor, performance, security")
    description: str = Field(description="Brief explanation of the changes")

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_CHANGELOG_TYPES:
            allowed = ", ".join(sorted(ALLOWED_CHANGELOG_TYPES))
            raise ValueError(f"type must be one of: {allowed}")
        return normalized

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("description must be non-empty")
        return normalized

class ChangelogResponse(BaseModel):
    entries: List[ChangelogEntry]

    @field_validator("entries")
    @classmethod
    def validate_entries(cls, value: List[ChangelogEntry]) -> List[ChangelogEntry]:
        if not value:
            raise ValueError("entries must contain at least one changelog entry")
        return value
