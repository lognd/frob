"""Data shapes ``frob.lang`` hands to ``frob.graph`` (docs/modules/graph.md).

Frozen pydantic models so a `ParsedFile` can be cached, hashed, and diffed
by identity-of-value rather than identity-of-object -- `frob.graph`'s
incremental rebuild depends on comparing two `ParsedFile`s for equality.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


# frob:doc docs/modules/lang.md#data-models
class SymbolKind(StrEnum):
    """The five extraction buckets every supported grammar collapses into."""

    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    CONST = "const"
    TYPE = "type"


# frob:doc docs/modules/lang.md#data-models
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


# frob:doc docs/modules/lang.md#data-models
class RawComment(BaseModel):
    """One extracted comment, with its binding to nearby symbols resolved."""

    model_config = ConfigDict(frozen=True)

    text: str
    span: tuple[int, int]
    enclosing: str | None
    following: str | None


# frob:doc docs/modules/dup.md#public-api
class TreeNode(BaseModel):
    """A simplified, language-agnostic subtree: a node's type label, its
    ordered children, and the byte span of the original source it covers
    -- comments and whitespace already stripped from `children`, but the
    `span` still covers the node's full original text.

    `frob.dup`'s R4 rung feeds this to `frob-core`'s Zhang-Shasha kernel
    (`_apted_similarity`) for a real tree-edit-distance comparison, rather
    than the flat leaf-token sequence `RawSymbol.body_tokens` exposes.
    `span` exists so `frob.dup._template` (docs/modules/dup-sota-survey.md
    sec 4) CAN slice literal source text for reverse-templating instead of
    rendering a structural `label(child, ...)` skeleton -- that consumer
    change is not made yet (tracked separately, out of `frob.lang`'s
    scope); today `span` is populated but unread outside this module.
    Frozen for the same identity-of-value reason as every other
    `frob.lang` model (docs/modules/graph.md).
    """

    model_config = ConfigDict(frozen=True)

    label: str
    span: tuple[int, int] = (0, 0)
    children: tuple["TreeNode", ...] = ()


# frob:doc docs/modules/lang.md#data-models
class ParsedFile(BaseModel):
    """The whole-file extraction result: symbols, comments, and a content hash."""

    model_config = ConfigDict(frozen=True)

    path: str
    language: str
    symbols: tuple[RawSymbol, ...]
    comments: tuple[RawComment, ...]
    content_hash: str
