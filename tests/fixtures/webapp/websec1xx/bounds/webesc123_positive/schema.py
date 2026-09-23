"""WEBSEC123 positive fixture: a pydantic field with no length bound."""

from pydantic import BaseModel, Field


class UserInput(BaseModel):
    name: str = Field(...)
