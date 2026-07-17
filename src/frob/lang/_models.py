"""Data shapes ``frob.lang`` hands to ``frob.graph`` (docs/graph.md).

Frozen pydantic models so a `ParsedFile` can be cached, hashed, and diffed
by identity-of-value rather than identity-of-object -- `frob.graph`'s
incremental rebuild depends on comparing two `ParsedFile`s for equality.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class SymbolKind(StrEnum):
    """The five extraction buckets every supported grammar collapses into."""

    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    CONST = "const"
    TYPE = "type"


class RawSymbol(BaseModel):
    """One extracted declaration: identity, publicness, span, and tokens."""

    model_config = ConfigDict(frozen=True)

    qualname: str
    kind: SymbolKind
    public: bool
    span: tuple[int, int]
    sig_tokens: tuple[str, ...]
    body_tokens: tuple[str, ...]
    doc_text: str


class RawComment(BaseModel):
    """One extracted comment, with its binding to nearby symbols resolved."""

    model_config = ConfigDict(frozen=True)

    text: str
    span: tuple[int, int]
    enclosing: str | None
    following: str | None


class ParsedFile(BaseModel):
    """The whole-file extraction result: symbols, comments, and a content hash."""

    model_config = ConfigDict(frozen=True)

    path: str
    language: str
    symbols: tuple[RawSymbol, ...]
    comments: tuple[RawComment, ...]
    content_hash: str
