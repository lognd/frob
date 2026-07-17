"""Data shapes for the obligation graph (docs/graph.md).

Every model is a frozen pydantic ``BaseModel`` so a `GraphSnapshot` can be
compared, cached, and diffed by identity-of-value -- the incremental build
and the lock/drift machinery both depend on structural equality, not object
identity.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from frob.lang import SymbolKind

__all__ = [
    "BuildStats",
    "Digests",
    "DriftReport",
    "DanglingEdge",
    "Edge",
    "EdgeKind",
    "GraphSnapshot",
    "LockEntry",
    "LockFile",
    "MalformedDirective",
    "StaleItem",
    "SymbolId",
    "SymbolKind",
    "SymbolRecord",
]


# frob:doc docs/graph.md#data-models
class SymbolId(BaseModel):
    """A symbol's identity: repo-relative path plus dotted qualname."""

    model_config = ConfigDict(frozen=True)

    path: str
    qualname: str

    def __str__(self) -> str:
        """Canonical `path::qualname` symref rendering."""
        return f"{self.path}::{self.qualname}"


# frob:doc docs/graph.md#data-models
class Digests(BaseModel):
    """The three independent sha256 digests tracked per symbol."""

    model_config = ConfigDict(frozen=True)

    sig: str
    body: str
    doc: str


# frob:doc docs/graph.md#data-models
class SymbolRecord(BaseModel):
    """One resolvable symbol: identity, kind, publicness, digests, span."""

    model_config = ConfigDict(frozen=True)

    id: SymbolId
    kind: SymbolKind
    public: bool
    digests: Digests
    span: tuple[int, int]

    @property
    # frob:doc docs/graph.md#data-models
    def symref(self) -> str:
        """The canonical `path::qualname` key this record is stored under."""
        return str(self.id)


# frob:doc docs/graph.md#data-models
class EdgeKind(StrEnum):
    """The typed relationships a `frob:` directive or doc anchor can declare."""

    DOC = "doc"
    USES_CONTRACT = "uses-contract"
    INVARIANT = "invariant"
    TICKET = "ticket"
    TODO = "todo"
    WAIVE = "waive"
    DESCRIBES = "describes"
    TESTS = "tests"
    DECISION = "decision"


# frob:doc docs/graph.md#data-models
class Edge(BaseModel):
    """One directive/anchor's declared obligation between a src and a target."""

    model_config = ConfigDict(frozen=True)

    src: str
    kind: EdgeKind
    target: str
    origin: str
    attrs: Mapping[str, str] = {}


# frob:doc docs/graph.md#data-models
class MalformedDirective(BaseModel):
    """A `frob:` comment line that failed to parse -- never silently dropped."""

    model_config = ConfigDict(frozen=True)

    file: str
    line: int
    reason: str


# frob:doc docs/graph.md#data-models
class BuildStats(BaseModel):
    """Per-`build_graph` counters proving incrementality to callers and tests."""

    model_config = ConfigDict(frozen=True)

    parsed: int
    cache_hits: int


# frob:doc docs/graph.md#data-models
class GraphSnapshot(BaseModel):
    """The whole obligation graph at one point in time: symbols, edges, hashes."""

    model_config = ConfigDict(frozen=True)

    root: str
    symbols: Mapping[str, SymbolRecord]
    edges: tuple[Edge, ...]
    malformed: tuple[MalformedDirective, ...] = ()
    file_hashes: Mapping[str, str] = {}
    stats: BuildStats = BuildStats(parsed=0, cache_hits=0)


# frob:doc docs/graph.md#data-models
class LockEntry(BaseModel):
    """One acknowledged (ref, facet) pair and the digest it was acked at."""

    model_config = ConfigDict(frozen=True)

    ref: str
    facet: str
    digest: str


# frob:doc docs/graph.md#data-models
class LockFile(BaseModel):
    """The full `frob.lock` document: a version tag plus sorted entries."""

    model_config = ConfigDict(frozen=True)

    version: int = 1
    entries: tuple[LockEntry, ...] = ()


# frob:doc docs/graph.md#data-models
class StaleItem(BaseModel):
    """A locked entry whose current digest no longer matches the ack."""

    model_config = ConfigDict(frozen=True)

    entry: LockEntry
    current: str
    dependents: tuple[str, ...]


# frob:doc docs/graph.md#data-models
class DanglingEdge(BaseModel):
    """An edge whose endpoint no longer resolves in the current snapshot."""

    model_config = ConfigDict(frozen=True)

    edge: Edge
    candidates: tuple[str, ...]


# frob:doc docs/graph.md#data-models
class DriftReport(BaseModel):
    """Pure comparison result between a `LockFile` and a `GraphSnapshot`."""

    model_config = ConfigDict(frozen=True)

    stale: tuple[StaleItem, ...]
    dangling: tuple[DanglingEdge, ...]
