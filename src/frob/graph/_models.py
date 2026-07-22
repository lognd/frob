"""Data shapes for the obligation graph (docs/modules/graph.md).

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
    "ParseFailure",
    "StaleItem",
    "SymbolId",
    "SymbolKind",
    "SymbolRecord",
]


# frob:doc docs/modules/graph.md#data-models
class SymbolId(BaseModel):
    """A symbol's identity: repo-relative path plus dotted qualname."""

    model_config = ConfigDict(frozen=True)

    path: str
    qualname: str

    def __str__(self) -> str:
        """Canonical `path::qualname` symref rendering."""
        return f"{self.path}::{self.qualname}"


# frob:doc docs/modules/graph.md#data-models
class Digests(BaseModel):
    """The three independent sha256 digests tracked per symbol."""

    model_config = ConfigDict(frozen=True)

    sig: str
    body: str
    doc: str


# frob:doc docs/modules/graph.md#data-models
class SymbolRecord(BaseModel):
    """One resolvable symbol: identity, kind, publicness, digests, span."""

    model_config = ConfigDict(frozen=True)

    id: SymbolId
    kind: SymbolKind
    public: bool
    digests: Digests
    span: tuple[int, int]

    @property
    # frob:doc docs/modules/graph.md#data-models
    def symref(self) -> str:
        """The canonical `path::qualname` key this record is stored under."""
        return str(self.id)


# frob:doc docs/modules/graph.md#data-models
class EdgeKind(StrEnum):
    """The typed relationships a `frob:` directive or doc anchor can declare."""

    DOC = "doc"
    USES_CONTRACT = "uses-contract"
    INVARIANT = "invariant"
    TICKET = "ticket"
    TODO = "todo"
    WAIVE = "waive"
    # T-0412: a TEMPORARY, ticket-bound, collected-before-release exception --
    # distinct from WAIVE's PERMANENT, forever-acceptable one.
    DEBT = "debt"
    DESCRIBES = "describes"
    TESTS = "tests"
    DECISION = "decision"
    CHANNEL = "channel"  # T-0080: binds code to a strata Flow id
    BOUNDARY = "boundary"  # T-0080: binds code to a strata Boundary id
    SECRET = "secret"  # T-0080: binds code to a strata Secret-clearance Node id
    # T-0428: binds a rule/detector's own code to a registry concept id it
    # claims to enforce (`docs/design/registry/*.yaml` entry ids) -- the
    # derived-coverage edge `frob.gates._registry_exhaustiveness` cross-
    # checks bidirectionally against hand-typed `handled_by:<rule-id>`
    # registry dispositions.
    ENFORCES = "enforces"
    # T-0576: `frob:debt` generalized to a public API's own sunset -- a
    # ticket-bound, dated exit for a symbol still callable today. Distinct
    # from DEBT (which suppresses a GATE FINDING) in that its subject is the
    # symbol's continued EXISTENCE: `frob.gates.deprecated_gate` warns while
    # `sunset` is still in the future and errors once it has passed or once
    # the owning ticket closes with the directive still in place.
    DEPRECATED = "deprecated"


# frob:doc docs/modules/graph.md#data-models
class Edge(BaseModel):
    """One directive/anchor's declared obligation between a src and a target."""

    model_config = ConfigDict(frozen=True)

    src: str
    kind: EdgeKind
    target: str
    origin: str
    attrs: Mapping[str, str] = {}


# frob:doc docs/modules/graph.md#data-models
class MalformedDirective(BaseModel):
    """A `frob:` comment line that failed to parse -- never silently dropped."""

    model_config = ConfigDict(frozen=True)

    file: str
    line: int
    reason: str


# frob:doc docs/modules/graph.md#data-models
# frob:ticket T-0558
# frob:ticket T-0561
class ParseFailure(BaseModel):
    """A source file `frob.lang.parse_file` could not parse at all (T-0558).

    Distinct from `MalformedDirective` (a single bad `frob:` comment line
    inside an otherwise-parsed file): a `ParseFailure` means the WHOLE
    file's symbols/edges/doc obligations are unknown for this build, not
    just one directive -- every gate that would have fired against that
    file's real content (COV001, DRIFT, INV, ...) instead sees nothing and
    passes vacuously. Never cached across builds (matching the pre-T-0558
    behavior of skipping `store_file_data` on a parse error), so a fixed
    file naturally drops out of this list on its next successful build.
    """

    model_config = ConfigDict(frozen=True)

    file: str
    reason: str


# frob:doc docs/modules/graph.md#data-models
class BuildStats(BaseModel):
    """Per-`build_graph` counters proving incrementality to callers and tests."""

    model_config = ConfigDict(frozen=True)

    parsed: int
    cache_hits: int


# frob:doc docs/modules/graph.md#data-models
# frob:ticket T-0558
# frob:ticket T-0561
class GraphSnapshot(BaseModel):
    """The whole obligation graph at one point in time: symbols, edges, hashes."""

    model_config = ConfigDict(frozen=True)

    root: str
    symbols: Mapping[str, SymbolRecord]
    edges: tuple[Edge, ...]
    malformed: tuple[MalformedDirective, ...] = ()
    parse_failures: tuple[ParseFailure, ...] = ()
    file_hashes: Mapping[str, str] = {}
    stats: BuildStats = BuildStats(parsed=0, cache_hits=0)


# frob:doc docs/modules/graph.md#data-models
class LockEntry(BaseModel):
    """One acknowledged (ref, facet) pair and the digest it was acked at."""

    model_config = ConfigDict(frozen=True)

    ref: str
    facet: str
    digest: str


# frob:doc docs/modules/graph.md#data-models
class LockFile(BaseModel):
    """The full `frob.lock` document: a version tag plus sorted entries."""

    model_config = ConfigDict(frozen=True)

    version: int = 1
    entries: tuple[LockEntry, ...] = ()


# frob:doc docs/modules/graph.md#data-models
class StaleItem(BaseModel):
    """A locked entry whose current digest no longer matches the ack."""

    model_config = ConfigDict(frozen=True)

    entry: LockEntry
    current: str
    dependents: tuple[str, ...]


# frob:doc docs/modules/graph.md#data-models
class DanglingEdge(BaseModel):
    """An edge whose endpoint no longer resolves in the current snapshot."""

    model_config = ConfigDict(frozen=True)

    edge: Edge
    candidates: tuple[str, ...]


# frob:doc docs/modules/graph.md#data-models
class DriftReport(BaseModel):
    """Pure comparison result between a `LockFile` and a `GraphSnapshot`."""

    model_config = ConfigDict(frozen=True)

    stale: tuple[StaleItem, ...]
    dangling: tuple[DanglingEdge, ...]
