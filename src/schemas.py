from typing import List
from pydantic import BaseModel, Field

class ChangelogEntry(BaseModel):
    type: str = Field(description="e.g. feat, fix, chore, docs, refactor, performance, security")
    description: str = Field(description="Brief explanation of the changes")

class ChangelogResponse(BaseModel):
    entries: List[ChangelogEntry]
