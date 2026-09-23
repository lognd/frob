"""WEBSEC123 negative fixture: the same field, with a max_length bound."""

from pydantic import BaseModel, Field


class UserInput(BaseModel):
    name: str = Field(..., max_length=100)
