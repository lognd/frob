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


# frob:ticket T-0433
# frob:ticket T-2231
# frob:doc docs/modules/lang.md#dependencies
# frob:tests tests/test_graph.py::TestBuildIncremental.test_fingerprint_packages_derived_from_lang_registry  # noqa: E501
# T-0433 (G6): the installed-distribution names whose VERSION changing can
# change what every non-`.strata` grammar in `frob.lang._EXTENSION_TABLE`
# parses to. `tree_sitter_language_pack.get_parser` is the ONE loading
# mechanism every tree-sitter language in `frob.lang` goes through -- so
# it, plus the `tree-sitter` core library it is built on, are the entire
# fingerprint surface for ALL six grammars today, not a per-language
# package. `frob.graph.cache._compute_fingerprint` derives its
# cache-invalidation fingerprint from this set (plus its own non-language
# packages, `frob` and `strata-core`) instead of hand-copying a tuple there
# -- adding a new `_EXTENSION_TABLE` grammar via `tree_sitter_language_pack`
# needs no fingerprint update at all; a language added through some OTHER
# package (a standalone `tree-sitter-<lang>` binding imported directly,
# bypassing the language pack) must be added here too, or a cache row for
# it can go stale exactly like the T-0243 incident this mechanism exists
# to prevent. T-2231: lives here (a pure leaf) rather than `frob.lang.
# __init__` -- `frob.graph.cache` needs this at module level, and
# `frob.lang.__init__` lazily imports `frob.graph.cache` back (T-1464), so
# defining it in the package body closed a real import cycle even though
# neither side ever runs its lazy import eagerly. Re-exported from `frob.
# lang.__init__` under this same name -- see that module's own comment.
GRAMMAR_FINGERPRINT_PACKAGES = frozenset({"tree-sitter", "tree-sitter-language-pack"})


# frob:doc docs/modules/lang.md#data-models
class RawSymbol(BaseModel):
    """One extracted declaration: identity, publicness, span, and tokens.

    `body_norm` (T-0334) is `body_tokens` re-expressed over a shared
    cross-grammar node-KIND vocabulary instead of literal leaf text: every
    identifier/literal leaf collapses to a generic `IDENT`/`LIT` tag and
    every keyword/punctuation leaf maps through `_common._CANONICAL_VOCAB`
    onto a canonical tag (python `def` and typescript `function` both
    become `FUNC_KW`, python `for ... in` and typescript `for ... of` both
    become `FOR_KW`/`ITER_KW`) -- see docs/modules/lang.md#the-token-contract.
    `frob.dup`'s R1-R3 bucket on literal `body_tokens`
    (tests/test_dup_cross_lang.py's T-0198 litmus proved that misses every
    cross-language clone by construction); `body_norm` exists so a
    follow-up to that pipeline can bucket on shared structure instead of
    shared spelling. Defaults to `()` for symbols with no body (`CONST`,
    `TYPE`, non-python `CLASS`) and for the strata walker, which has no
    tree-sitter node kinds to map through.
    """

    model_config = ConfigDict(frozen=True)

    qualname: str
    kind: SymbolKind
    public: bool
    span: tuple[int, int]
    sig_tokens: tuple[str, ...]
    body_tokens: tuple[str, ...]
    doc_text: str
    body_norm: tuple[str, ...] = ()


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

    `field` (T-0495) is this node's tree-sitter FIELD NAME as seen from
    its own parent (`Node.field_name_for_child`), or `None` for a node
    with no field name (an unlabeled/anonymous child, or the tree root).
    Some grammars distinguish two structurally-identical-looking sibling
    positions only by field name, never by a wrapping node label --
    e.g. rust's `parameter` node has a `pattern` field (the parameter
    name) and a `type` field (its type annotation) as direct, unwrapped
    siblings, unlike python/typescript which wrap a type annotation in
    its own `type`/`type_annotation` node. `frob.dup._template`'s
    type-hole classification (T-0287) reads `field` to extend TYPE-hole
    recognition to rust/c/cpp, which the label-only shape before T-0495
    could not express.
    Frozen for the same identity-of-value reason as every other
    `frob.lang` model (docs/modules/graph.md).
    """

    model_config = ConfigDict(frozen=True)

    label: str
    span: tuple[int, int] = (0, 0)
    children: tuple["TreeNode", ...] = ()
    field: str | None = None


# frob:doc docs/modules/lang.md#data-models
class ParsedFile(BaseModel):
    """The whole-file extraction result: symbols, comments, and a content hash."""

    model_config = ConfigDict(frozen=True)

    path: str
    language: str
    symbols: tuple[RawSymbol, ...]
    comments: tuple[RawComment, ...]
    content_hash: str
