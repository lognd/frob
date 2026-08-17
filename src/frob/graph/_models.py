"""Data shapes for the obligation graph (docs/modules/graph.md).

Every model is a frozen pydantic ``BaseModel`` so a `GraphSnapshot` can be
compared, cached, and diffed by identity-of-value -- the incremental build
and the lock/drift machinery both depend on structural equality, not object
identity.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from frob.lang._models import SymbolKind

__all__ = [
    "AckAuditEntry",
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
    # T-0744: typestate protocol declaration surface (child 1 of the T-0739
    # umbrella). PROTOCOL declares a named state machine (`states=`,
    # `initial=`, optional `cleanup=`) at the src the directive binds to
    # (or, for a name-pattern-inferred protocol, at the enclosing file).
    PROTOCOL = "protocol"
    # T-0744: a function's declared state TRANSITION within a protocol
    # (`proto=`, `from=`, `to=`) -- `target` is the protocol name, `src` is
    # the transitioning function.
    TRANSITION = "transition"
    # T-0744: a function's declared state REQUIREMENT within a protocol
    # (`proto=`, `state=`) -- `target` is the protocol name, `src` is the
    # function only callable while that state holds. Verification of these
    # requirements against the call graph is later T-0739 children, out of
    # this module's scope; this module only parses the declaration.
    REQUIRES = "requires"
    # T-0809: resource-tracking DSL, the "acquired/released/escaped
    # resources" third of the T-0745 protocol-summary shape (the design
    # sketch T-0745 itself deferred). `target` is the resource name (a
    # plain string, e.g. "fd", "lock", "conn" -- opaque, like every other
    # DSL target). ACQUIRE/RELEASE mark the declaring function as directly
    # acquiring/releasing that resource; ESCAPES marks it as transferring
    # an acquired-but-unreleased resource out to its caller (e.g. returned
    # or stored) rather than releasing it itself. Real postdominance-based
    # cleanup-obligation VERIFICATION (does every acquire actually get
    # released on every exit) is T-0747, blocked on this ticket plus
    # T-0686 -- this module only parses the declaration and folds it into
    # `frob.graph.summary.FunctionSummary`'s transitive resource sets.
    ACQUIRE = "acquire"
    RELEASE = "release"
    ESCAPES = "escapes"
    # T-1227: `frob:enumerates` -- binds a doc span to a named collection
    # literal (dict/set/tuple/Literal/ErrorSet/StrEnum) whose members the
    # doc claims to enumerate. The code-side form (`_VERB_TABLE`, bare
    # target = doc anchor, mirroring `DOC`'s own code->doc direction) is
    # emitted from the collection literal's own symbol; the markdown-side
    # form (`markdown_anchors`, mirroring `DESCRIBES`) is emitted from the
    # doc anchor with an explicit `members="a,b,c"` attribute -- the
    # doc-authored CLAIM the DOCENUM001 gate (`frob.gates._docenum`)
    # AST-diffs against the literal's actual members at check time,
    # independent of ack state (content-verified, ack-immune, unlike
    # DRIFT001's digest-based staleness check).
    ENUMERATES = "enumerates"
    # T-1229: `frob:until T-####` -- markdown-side directive
    # (`markdown_anchors`, mirroring DESCRIBES/ENUMERATES' anchor-binding
    # shape) that binds a not-yet-built prose claim to the ticket that will
    # build it: `target` is the ticket id, `src` is `<doc>#<anchor>`. The
    # NEGEXIST001 gate (`frob.gates._negexist`) treats the claim as stale
    # once that ticket closes/archives (the prose should have been updated
    # when the ticket shipped) and flags a negative-existence claim in the
    # same anchor section with no `frob:until` at all as unbound.
    UNTIL = "until"
    # T-1229: a heuristically-detected "does not exist yet"/"not yet
    # built"/... prose claim (`_NEGEXIST_PHRASE_RE`), emitted alongside
    # UNTIL from the same `markdown_anchors` pass so both flow into
    # `GraphSnapshot.edges` uniformly -- `target` is the matched phrase
    # snippet (diagnostic only, never machine-compared), `src` is
    # `<doc>#<anchor>`. NEGEXIST001 groups these by anchor against any
    # sibling UNTIL edge to decide bound vs. unbound.
    CLAIMS_ABSENCE = "claims-absence"


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


# frob:ticket T-1317
# frob:doc docs/modules/gates.md#ack-accountability-t-1317
class AckAuditEntry(BaseModel):
    """One append-only audit line for a `frob ack` mutation (T-1317): the
    `ScopeChangeEntry`/`AcceptanceAmendmentEntry`/`EvidenceChangeEntry`
    discipline (T-0455/T-1422/T-1733) applied to `frob.lock` -- `frob ack`
    is the one place the obligation graph accepts a HUMAN ASSERTION
    (a re-verified doc is still true) in place of a mechanical check, so an
    ack with no reason and no record of what it vouched for is
    indistinguishable from a rubber stamp. `reason` is mandatory (`frob.
    graph.lock.acknowledge` refuses with `LockError.AckReasonMissing` when
    blank or boilerplate-detected -- see `_reject_boilerplate_reason`).
    `old_digest` is `None` only for a genuinely first-ever ack of this
    `(ref, facet)` pair -- never a stand-in for "delta could not be
    computed"; `acknowledge` computes it from the entries dict it already
    holds BEFORE overwriting them, so the delta is always the true
    before/after pair, not a guess. Never edited or removed once written,
    only appended to."""

    model_config = ConfigDict(frozen=True)

    ref: str
    facet: str
    old_digest: str | None
    new_digest: str
    reason: str
    actor: str
    at: date


# frob:doc docs/modules/graph.md#data-models
class LockFile(BaseModel):
    """The full `frob.lock` document: a version tag, sorted entries, and
    the append-only `frob ack` audit trail (`ack_log`, T-1317) recording
    every reason and digest delta an ack ever vouched for."""

    model_config = ConfigDict(frozen=True)

    version: int = 1
    entries: tuple[LockEntry, ...] = ()
    ack_log: tuple[AckAuditEntry, ...] = ()


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
