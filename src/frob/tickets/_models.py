"""Data models and error types for frob.tickets
(docs/modules/tickets.md is authoritative)."""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Mapping, Sequence
from datetime import date
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator
from typani.error_set import ErrorSet


# frob:doc docs/modules/tickets.md#data-models
# frob:doc docs/guides/extending/ticket-kinds-states.md#ticket-kinds-and-states
class TicketState(StrEnum):
    """The six states a ticket can occupy in the queue state machine."""

    QUEUED = "queued"
    PLANNED = "planned"
    IN_PROGRESS = "in-progress"
    BLOCKED = "blocked"
    DONE = "done"
    DROPPED = "dropped"


# frob:doc docs/modules/tickets.md#data-models
class TicketKind(StrEnum):
    """What kind of work a ticket represents."""

    FEATURE = "feature"
    BUG = "bug"
    SECURITY = "security"
    UX = "ux"
    DOCS = "docs"
    INVARIANT = "invariant"
    INCIDENT = "incident"


# frob:doc docs/modules/tickets.md#public-api
# T-0215: docs/design tickets (no pytest surface of their own) may close on
# a vetted shell command's exit status + output digest instead of pytest
# node ids. Code kinds (bug/feature/security/...) are excluded on purpose.
# Lives in `_models.py` (not `__init__.py`, where the record-time
# `add_cmd_evidence` primitive lives) so BOTH `frob.tickets.__init__`
# (record + close-time guard) and `frob.tickets._land` (land-time guard)
# can import it without a circular import -- `_land` is imported BY
# `__init__.py`, so the reverse import is not available there.
CMD_EVIDENCE_ALLOWED_KINDS = frozenset({TicketKind.DOCS})

# The exact shape `run_cmd_evidence` writes: `cmd:<command> exit=0
# sha256=<12-hex>`. Single source of truth for "does this evidence string
# look like a cmd: entry" -- `frob.gates`'s COV003 check and every
# kind-consistency guard (`_transition_guard`, `_land._validate_closeable`)
# match against this SAME regex (imported, never reimplemented) so the
# record-time shape and every later recognition of a cmd: entry can never
# drift apart (T-0215 review round 2).
_CMD_EVIDENCE_RE = re.compile(r"^cmd:.+ exit=0 sha256=[0-9a-f]{12}$")


# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_cmd_evidence.py::TestIsCmdEvidence.test_shapes
def is_cmd_evidence(entry: str) -> bool:
    """Whether `entry` has the `cmd:<command> exit=0 sha256=<12-hex>` shape
    `run_cmd_evidence` writes -- the format test `frob.gates`'s COV003 and
    the kind-consistency close/land guards use to recognize a cmd: entry
    without re-running anything (T-0215). NOT a validity check by itself:
    callers additionally gate on ticket kind (only `docs` may carry a
    cmd: entry) -- this only answers "does it have the shape," so a
    malformed prefix (typo'd, hand-edited) correctly falls through to the
    pytest-node-id check instead and fails there too.
    """
    return bool(_CMD_EVIDENCE_RE.match(entry))


# frob:doc docs/modules/tickets.md#public-api
# The ledger every ticket op reads/writes on every invocation -- always
# implicitly in scope so recording a Done report or evidence never itself
# trips SCOPE001 (T-0241).
LEDGER_PATH = "tickets.md"

# frob:ticket T-0446
# frob:doc docs/modules/tickets.md#public-api
# The three files EVERY new `frob ticket <subcommand>` structurally must
# touch to actually wire the command in: the dispatch table (`__main__.py`),
# the CLI flags it reads (`app/config.py`), and the runner that implements
# it (`app/ticket_runner.py`). T-0323 (git-merge-driver ticket, adding `frob
# ticket merge-driver`) needed all three despite a scope declared as
# `src/frob/tickets/**` -- every feature ticket that adds a subcommand hits
# this same "scope-expansion ceremony" (a `frob ticket scope --add` per
# wiring file, every time) because these files are structurally required
# but never anticipated at ticket-filing time. Implicitly in scope for any
# `TicketKind.FEATURE` ticket, the same LEDGER_PATH-always-in-scope pattern
# T-0241 established for tickets.md -- NOT extended to every kind, since a
# bug/docs/security ticket touching the CLI dispatch table unannounced is
# exactly the scope-creep SCOPE001 exists to catch.
CLI_WIRING_FILES = frozenset(
    {
        "src/frob/__main__.py",
        "src/frob/app/config.py",
        "src/frob/app/ticket_runner.py",
    }
)


# frob:tests tests/test_tickets.py::TestScopeMatching.test_comma_joined_entry_splits
def _split_scope_entries(raw: Sequence[str]) -> tuple[str, ...]:
    """Split each entry of `raw` on commas and strip whitespace.

    A hand-typed or scripted `--scope 'a/,b/,c/'` previously became ONE
    fnmatch pattern (`"a/,b/,c/"`) that could never match any real path --
    SCOPE001 fired on every touched file and pre-work sweeps recorded
    against zero files (T-0241). Applied at model-construction time so it
    normalizes both freshly created tickets and tickets loaded from a
    hand-edited ledger.
    """
    entries: list[str] = []
    for item in raw:
        for piece in item.split(","):
            piece = piece.strip()
            if piece:
                entries.append(piece)
    return tuple(entries)


# frob:tests tests/test_tickets.py::TestScopeMatching.test_dir_prefix_globs_recursively
# frob:tests tests/test_tickets.py::TestScopeMatching.test_bare_dir_entry_no_trailing_slash_globs_recursively  # noqa: E501
def _scope_globs(scope: Sequence[str]) -> tuple[str, ...]:
    """Expand a ticket's declared `scope` into concrete fnmatch patterns.

    A bare directory prefix (`design/`, no glob metacharacters) previously
    matched nothing since fnmatch treats it as a literal string equal to
    the path -- expand it to `design/**` so it recurses. A directory entry
    typed WITHOUT the trailing slash (`docs/modules`, no glob
    metacharacters and no dot-extension on its last path segment) is the
    same trap in a different shape: fnmatch treats it as a literal string
    that can never match a real file path underneath it, so it silently
    drops out of scope (T-0521 -- T-0515 hit this directly with
    `docs/modules`/`docs/strata` entries). Both the entry itself (so a
    ticket can still scope-lease the directory path used as a doc anchor)
    and its `/**` recursive expansion are added, matching the
    trailing-slash case's semantics. An entry with a dot-extension in its
    final segment (`src/frob/foo.py`) is always a literal file reference,
    never a directory, and is left untouched. `LEDGER_PATH` is always
    appended so the ledger is implicitly in scope for every ticket
    (T-0241).
    """
    globs: list[str] = []
    for entry in scope:
        has_glob_chars = any(ch in entry for ch in "*?[")
        if entry.endswith("/") and not has_glob_chars:
            globs.append(entry + "**")
        elif not has_glob_chars and "." not in entry.rsplit("/", 1)[-1]:
            # Bare directory name with no trailing slash, e.g. "docs/modules":
            # not a glob and not a file (no extension on its last segment) --
            # treat as an implied directory prefix (T-0521).
            globs.append(entry)
            globs.append(entry + "/**")
        else:
            globs.append(entry)
    if LEDGER_PATH not in globs:
        globs.append(LEDGER_PATH)
    return tuple(globs)


# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets.py::TestScopeMatching.test_ledger_always_in_scope
# frob:tests tests/test_tickets.py::TestScopeMatching.test_feature_kind_implies_cli_wiring_files_in_scope  # noqa: E501
def scope_matches(
    path: str, scope: Sequence[str], *, kind: TicketKind | None = None
) -> bool:
    """Whether `path` is covered by a ticket's declared `scope`.

    THE one implementation every scope-consulting site (`frob.tickets`'s
    own land-time check, `frob.gates`'s SCOPE001/PRE001/scope-digest
    checks) must call, so `dir/` glob expansion and the implicit-ledger
    rule can never drift between two independent copies (T-0241). Re-splits
    comma-joined entries defensively even though `Ticket`/`TicketSpec`
    normalize on construction, so a raw, un-modeled `scope` sequence passed
    directly still matches correctly.

    T-0446: when `kind` is `TicketKind.FEATURE`, `CLI_WIRING_FILES` is ALSO
    implicitly in scope, mirroring the `LEDGER_PATH`-always-in-scope
    pattern above -- a feature ticket adding a new `frob ticket <cmd>`
    structurally needs to touch the dispatch table/config/runner wiring no
    matter what its author anticipated when filing it. `kind=None` (the
    default, and every pre-T-0446 call site) preserves the exact prior
    behavior unchanged."""
    globs = _scope_globs(_split_scope_entries(scope))
    if kind is TicketKind.FEATURE:
        globs = (*globs, *CLI_WIRING_FILES)
    return any(fnmatch.fnmatch(path, glob) for glob in globs)


# frob:ticket T-0453
def _tokenize_glob(pattern: str) -> tuple[str, ...]:
    """Tokenize an fnmatch pattern into single-char literal tokens plus a
    `'*'` (any-length wildcard) token and a `'?'` (any-single-char) token
    -- a `[...]` bracket class collapses to one `'?'` token since fnmatch
    itself only ever consumes exactly one character for it. Feeds
    `_globs_intersect`'s pattern-vs-pattern DP (T-0453)."""
    tokens: list[str] = []
    i = 0
    n = len(pattern)
    while i < n:
        ch = pattern[i]
        if ch in "*?":
            tokens.append(ch)
            i += 1
        elif ch == "[":
            close = pattern.find("]", i + 1)
            tokens.append("?")
            i = (close + 1) if close != -1 else n
        else:
            tokens.append(ch)
            i += 1
    return tuple(tokens)


# frob:ticket T-0453
# frob:tests tests/test_tickets_lease.py::TestGlobsIntersect.test_wildcard_prefix_overlaps_literal  # noqa: E501
# frob:tests tests/test_tickets_lease.py::TestGlobsIntersect.test_disjoint_literal_siblings  # noqa: E501
def _globs_intersect(glob_a: str, glob_b: str) -> bool:
    """Whether two fnmatch-style glob patterns can ever match the SAME
    concrete path -- a sound path/glob intersection test (T-0453 DESIGN
    CORRECTION), not a literal-prefix heuristic: `'*'` matches any
    (possibly empty) run of characters and `'?'`/a bracket class matches
    exactly one, on EITHER side, via the standard two-pattern wildcard-
    intersection DP (memoized over token positions). This is what keeps
    the T-0453 scope-lease overlap check sound for arbitrary globs -- not
    just the `dir/**`-vs-literal-file case, and specifically NOT special-
    casing `tests/**`/`docs/` out of the comparison (the thing the design
    correction says never to do).
    """
    tok_a = _tokenize_glob(glob_a)
    tok_b = _tokenize_glob(glob_b)
    memo: dict[tuple[int, int], bool] = {}

    def rec(i: int, j: int) -> bool:
        key = (i, j)
        if key in memo:
            return memo[key]
        if i == len(tok_a) and j == len(tok_b):
            result = True
        elif i < len(tok_a) and tok_a[i] == "*":
            result = rec(i + 1, j) or (j < len(tok_b) and rec(i, j + 1))
        elif j < len(tok_b) and tok_b[j] == "*":
            result = rec(i, j + 1) or (i < len(tok_a) and rec(i + 1, j))
        elif i < len(tok_a) and j < len(tok_b):
            a_tok, b_tok = tok_a[i], tok_b[j]
            result = (a_tok == "?" or b_tok == "?" or a_tok == b_tok) and rec(
                i + 1, j + 1
            )
        else:
            result = False
        memo[key] = result
        return result

    return rec(0, 0)


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_lease.py::TestScopeOverlap.test_precise_scopes_disjoint
# frob:tests tests/test_tickets_lease.py::TestScopeOverlap.test_real_collision_detected
def scope_overlap_globs(
    scope_a: Sequence[str], scope_b: Sequence[str]
) -> tuple[str, str] | None:
    """First colliding `(glob_from_a, glob_from_b)` pair between two
    tickets' declared scopes, or `None` if provably disjoint (T-0453).

    `LEDGER_PATH` is dropped from BOTH sides first: every ticket implicitly
    leases it via `_scope_globs`, so leaving it in would make every ticket
    pair collide on `tickets.md` alone (the over-hiding bug the T-0453
    DESIGN CORRECTION fixes) -- it is the ONLY path ignored in the overlap
    check; `tests/**`/`docs/` are deliberately NOT special-cased out here.
    """
    globs_a = [g for g in _scope_globs(scope_a) if g != LEDGER_PATH]
    globs_b = [g for g in _scope_globs(scope_b) if g != LEDGER_PATH]
    for glob_a in globs_a:
        for glob_b in globs_b:
            if _globs_intersect(glob_a, glob_b):
                return (glob_a, glob_b)
    return None


# frob:ticket T-0485
# frob:tests tests/test_tickets_scope_mutation.py::TestGlobIsSubset.test_concrete_path_under_double_star_is_subset  # noqa: E501
# frob:tests tests/test_tickets_scope_mutation.py::TestGlobIsSubset.test_wildcard_bearing_narrow_is_never_subset  # noqa: E501
def _glob_is_subset(narrow: str, broad: str) -> bool:
    """Whether every path `narrow` can match is also matched by `broad` --
    decided EXACTLY when `narrow` denotes one concrete literal path (no
    `*`/`?`/`[...]`), by delegating to `fnmatch.fnmatch(narrow, broad)`
    (narrow's matched set is then the singleton `{narrow}`, so this is
    precise, not a heuristic). Conservatively `False` whenever `narrow`
    itself still carries a wildcard: a wildcard-bearing glob's full matched
    set is not proven a subset by this check, so a genuine scope expansion
    can never slip through disguised as a 'narrowing' add (T-0485)."""
    if any(ch in narrow for ch in "*?["):
        return False
    return fnmatch.fnmatch(narrow, broad)


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_lease.py::TestScopeOverlap.test_precise_scopes_disjoint
def scope_overlap(scope_a: Sequence[str], scope_b: Sequence[str]) -> bool:
    """Whether two tickets' declared scopes could ever both match the same
    real path -- the T-0453 scope-lease collision test `doable` filters
    queued/planned candidates through against every in-progress ticket."""
    return scope_overlap_globs(scope_a, scope_b) is not None


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
# T-0453 DESIGN CORRECTION: these are the specific globs that have
# actually caused over-hiding in this repo's history (nearly every ticket
# declares `tests/**` and/or `docs/`) -- flagged unconditionally by
# `large_glob_warnings`, before the file-count threshold is even
# consulted, as a nudge to narrow to the precise files a ticket touches.
OVER_BROAD_LITERAL_GLOBS = frozenset(
    {
        "tests/**",
        "tests/",
        "src/frob/**",
        "src/frob/",
        "docs/",
        "docs/**",
    }
)


# frob:ticket T-0398
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_evidence_integrity.py::TestD11DedupedMatchRule.test_tickets_and_gates_share_matches_collected  # noqa: E501
def matches_collected(evidence: str, collected: frozenset[str]) -> bool:
    """Exact node-id membership, or bare-function match for parametrized
    tests (`f` satisfies evidence when only `f[param]` variants collect).

    THE single implementation of "collected" resolution -- `frob.tickets`
    (`add_evidence`) and `frob.gates` (COV003) both call this instead of
    keeping two independently-hand-written copies of the same regex-free
    matching rule (D-11: the two copies could desync silently; gates may
    import from tickets since gates already sits above tickets in the
    dependency graph, so this is a one-way, cycle-free consolidation)."""
    if evidence in collected:
        return True
    prefix = evidence + "["
    return any(node.startswith(prefix) for node in collected)


# frob:doc docs/modules/tickets.md#public-api
# T-0458: public (no leading underscore) so `frob.tickets.compose_done_report`
# can reuse the SAME heading string `has_substantive_done_report`/
# `replace_done_report_section` key off, rather than a second hand-typed
# copy that could silently drift out of sync with what the D-03 check
# recognizes as a real Done-report heading.
DONE_REPORT_HEADING = "## Done report"
_DONE_REPORT_HEADING = DONE_REPORT_HEADING
# D-03: a bare heading with nothing under it (or only blank lines)
# previously satisfied close/land (`_has_done_report`'s old shape). The bar
# is deliberately minimal -- 1 non-blank line, a handful of characters --
# so it rejects only a truly EMPTY section (the fabrication this finding is
# about) and never blocks a genuine, even terse, one-line Done report (this
# repo's own test fixtures routinely use short bodies like "All good." or
# "smoke" as a legitimate Done report).
_MIN_DONE_REPORT_CHARS = 3
_MIN_DONE_REPORT_LINES = 1


# frob:ticket T-0493
def _done_report_section_end(lines: list[str], heading_idx: int) -> int:
    """The index one past the END of the `## Done report` section starting
    at `heading_idx`: the next `## ` heading that is NOT itself another
    `## Done report` heading, or `len(lines)`.

    T-0493: a stray, empty `## Done report` heading (hand-typed as a
    placeholder, or left behind by an earlier corrupted write) sitting
    BEFORE the real, substantive one must not be treated as its own
    section boundary -- doing so is exactly what let a duplicate heading
    persist forever: `has_substantive_done_report` would only ever see the
    empty first section (rejecting a genuinely-done ticket as
    `MissingEvidence`), and `replace_done_report_section` would only ever
    overwrite that first, empty section, leaving the second, real one
    stuck untouched on every subsequent write. Treating a REPEATED
    `## Done report` heading as still part of the same section (skip past
    it, keep scanning) means both functions see -- and, for the write
    side, collapse -- the WHOLE run of Done-report headings as one
    section, so a stray duplicate self-heals the next time either runs."""
    end_idx = len(lines)
    for i in range(heading_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped == _DONE_REPORT_HEADING:
            continue
        if stripped.startswith("## "):
            end_idx = i
            break
    return end_idx


def _done_report_section_lines(body: str) -> list[str] | None:
    """The raw lines of body's `## Done report` section (up to the next
    non-Done-report `## ` heading or EOF, T-0493), or `None` if no such
    heading exists."""
    lines = body.splitlines()
    heading_idx = None
    for i, line in enumerate(lines):
        if line.strip() == _DONE_REPORT_HEADING:
            heading_idx = i
            break
    if heading_idx is None:
        return None
    end_idx = _done_report_section_end(lines, heading_idx)
    return lines[heading_idx + 1 : end_idx]


# frob:ticket T-0398
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_evidence_integrity.py::TestD03SubstantiveDoneReport.test_empty_section_rejected  # noqa: E501
def has_substantive_done_report(body: str) -> bool:
    """Whether `body` carries a `## Done report` heading AND a real section
    under it (D-03) -- `frob.tickets.__init__` (`_done_transition_guard`)
    and `frob.tickets._land` (`_validate_closeable`, `_newer`) both call
    this single implementation (also dedupes the two independent
    heading-only copies those two modules used to carry). A section is
    "real" if it has at least `_MIN_DONE_REPORT_LINES` non-blank lines and
    at least `_MIN_DONE_REPORT_CHARS` of non-whitespace content -- low
    enough to never block a genuine terse report, high enough to reject a
    bare `## Done report\n` heading or a couple of blank lines under it."""
    section = _done_report_section_lines(body)
    if section is None:
        return False
    non_blank = [line for line in section if line.strip()]
    content = "\n".join(non_blank)
    return (
        len(non_blank) >= _MIN_DONE_REPORT_LINES
        and len(content) >= _MIN_DONE_REPORT_CHARS
    )


# frob:ticket T-0458
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestReplaceDoneReportSection.test_replaces_existing_section  # noqa: E501
def replace_done_report_section(body: str, new_section: str) -> str:
    """Splice `new_section` (a full `## Done report\\n...` block) into `body`,
    replacing any existing '## Done report' section (heading through the
    next top-level '## ' heading or EOF) verbatim, or appending it at the
    end if no such heading exists yet.

    THE block-boundary-aware primitive `frob.tickets.set_done_report` uses
    so a caller composing a Done report never hand-slices markdown itself
    (T-0458) -- the exact hand-edit failure mode (an Edit call landing
    mid-section, or missing the next `## ` boundary) that repeatedly
    corrupted `tickets.md` this session.

    T-0493: if MORE THAN ONE `## Done report` heading is already present
    (e.g. a stray empty placeholder left before a real one), the entire
    run of them -- from the FIRST heading through whatever follows the
    LAST one (`_done_report_section_end`'s repeated-heading skip, T-0493)
    -- is replaced, not just the first. Otherwise a stray heading, once
    introduced by any means, could never be cleared: this function would
    keep overwriting only the empty first section forever, leaving a
    real second one stuck untouched.
    """
    lines = body.splitlines()
    heading_idx = None
    for i, line in enumerate(lines):
        if line.strip() == _DONE_REPORT_HEADING:
            heading_idx = i
            break
    new_lines = new_section.rstrip("\n").splitlines()
    if heading_idx is None:
        separator: list[str] = [] if not lines or lines[-1] == "" else [""]
        return "\n".join([*lines, *separator, *new_lines]) + "\n"
    end_idx = _done_report_section_end(lines, heading_idx)
    before, after = lines[:heading_idx], lines[end_idx:]
    result = [*before, *new_lines]
    if after:
        result = [*result, "", *after]
    return "\n".join(result) + "\n"


# frob:doc docs/modules/tickets.md#data-models
class Stride(StrEnum):
    """STRIDE threat categories for kind=security tickets (T-0007)."""

    SPOOFING = "spoofing"
    TAMPERING = "tampering"
    REPUDIATION = "repudiation"
    INFO_DISCLOSURE = "info-disclosure"
    DENIAL_OF_SERVICE = "denial-of-service"
    ELEVATION_OF_PRIVILEGE = "elevation-of-privilege"


# frob:ticket T-0411
# frob:doc docs/modules/tickets.md#data-models
class Priority(StrEnum):
    """How important a ticket is, independent of age (T-0411): `doable`
    orders on this first so a high-value ticket never rots invisibly
    behind a pile of older low-value ones. Default is MEDIUM so every
    ticket created before this field existed (and any new one that omits
    `--priority`) keeps its prior age-only ordering relative to peers."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# frob:ticket T-0411
# frob:doc docs/modules/tickets.md#data-models
# frob:tests tests/test_tickets_priority.py::TestPriorityRank.test_critical_outranks_low
PRIORITY_RANK: dict[Priority, int] = {
    Priority.LOW: 0,
    Priority.MEDIUM: 1,
    Priority.HIGH: 2,
    Priority.CRITICAL: 3,
}


# frob:doc docs/modules/tickets.md#data-models
class Origin(StrEnum):
    """Who filed a ticket."""

    HUMAN = "human"
    AGENT = "agent"
    AUDITOR = "auditor"


# frob:doc docs/modules/tickets.md#data-models
class Attachment(BaseModel):
    """One image/file attached to a ticket, with integrity hash."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    caption: str
    sha256: str


# frob:doc docs/modules/tickets.md#data-models
class FailureEntry(BaseModel):
    """One line of append-only cross-session failure memory for a ticket."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    date: date
    attempt: int
    summary: str


# frob:ticket T-0455
# frob:doc docs/modules/tickets.md#data-models
class ScopeChangeOp(StrEnum):
    """Whether a `scope_changes` audit entry expanded or reduced a ticket's
    declared scope (T-0455)."""

    ADD = "add"
    REMOVE = "remove"


# frob:ticket T-0455
# frob:doc docs/modules/tickets.md#data-models
class ScopeChangeEntry(BaseModel):
    """One append-only audit line for a `frob ticket scope --add/--remove`
    mutation (T-0455): what glob moved, which direction, why, who did it,
    and when -- the formal, accountable replacement for the ad-hoc SCOPE001
    waive dodge. Never edited or removed once written, only appended to."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    op: ScopeChangeOp
    glob: str
    reason: str
    actor: str
    at: date


# frob:doc docs/modules/tickets.md#data-models
class Ticket(BaseModel):
    """One ticket: frontmatter fields plus the verbatim markdown body."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    title: str
    state: TicketState
    kind: TicketKind
    origin: Origin
    created: date
    # frob:ticket T-0411
    priority: Priority = Priority.MEDIUM
    blocked_by: tuple[str, ...] = ()
    parent: str | None = None
    scope: tuple[str, ...] = ()
    # frob:ticket T-0455
    # append-only audit trail of every `frob ticket scope --add/--remove`
    # mutation this ticket's `scope` has gone through (never edited, only
    # appended) -- makes scope creep visible instead of a silent SCOPE001
    # waive.
    scope_changes: tuple[ScopeChangeEntry, ...] = ()
    evidence: tuple[str, ...] = ()
    attachments: tuple[Attachment, ...] = ()
    # given/when/then acceptance criteria the reviewer verifies (T-0006)
    acceptance: tuple[str, ...] = ()
    # STRIDE category for kind=security tickets (T-0007)
    threat: Stride | None = None
    body: str = ""

    @field_validator("scope", mode="before")
    @classmethod
    def _normalize_scope(cls, value: Sequence[str]) -> tuple[str, ...]:
        """Split any comma-joined entry into separate globs on load or
        construction (T-0241) -- see `_split_scope_entries`."""
        return _split_scope_entries(value)


# frob:doc docs/modules/tickets.md#data-models
class TicketSpec(BaseModel):
    """Input to new_ticket; id/created/state are assigned by the library."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    kind: TicketKind
    origin: Origin
    # frob:ticket T-0411
    priority: Priority = Priority.MEDIUM
    scope: tuple[str, ...] = ()
    blocked_by: tuple[str, ...] = ()
    parent: str | None = None
    acceptance: tuple[str, ...] = ()
    threat: Stride | None = None
    evidence: tuple[str, ...] = ()
    body: str = ""

    @field_validator("scope", mode="before")
    @classmethod
    def _normalize_scope(cls, value: Sequence[str]) -> tuple[str, ...]:
        """Split any comma-joined entry into separate globs before the spec
        is turned into a `Ticket` (T-0241) -- see `_split_scope_entries`."""
        return _split_scope_entries(value)


# frob:doc docs/modules/tickets.md#data-models
# frob:ticket T-0162
class RenumberReport(BaseModel):
    """Outcome of `renumber_one`/`finalize_draft`: what changed (or would
    change, under `--dry-run`) rewriting one ticket id everywhere."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    old_id: str
    new_id: str
    ledger_changed: bool
    files_changed: tuple[str, ...]
    occurrences: int
    dry_run: bool


# frob:doc docs/modules/tickets.md#data-models
class TicketQueue(BaseModel):
    """The full set of tickets loaded from tickets/, keyed by id."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tickets: Mapping[str, Ticket]


# frob:doc docs/modules/tickets.md#data-models
class AttachmentSource(BaseModel):
    """Where attach() should read image bytes from; None path means clipboard."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: Path | None = None


# frob:doc docs/modules/tickets.md#error-types
class TicketError(ErrorSet):
    """Fallible outcomes of frob.tickets queue/mutation operations."""

    NotFound = "No ticket with that id"
    DuplicateId = "Ticket id already exists"
    MalformedFrontmatter = "Ticket file failed schema validation"
    InvalidTransition = "State change not allowed by the state machine"
    MissingEvidence = "done requires evidence and a Done report"
    MalformedEvidence = "evidence entry failed schema validation"
    BlockerOpen = "Cannot start: blocked_by contains open tickets"
    WriteFailed = "Atomic ticket write failed"
    UnknownEvidence = "Evidence id does not resolve to a collected test"
    # T-0215: non-pytest evidence channel for docs-kind tickets
    EvidenceKindNotAllowed = "cmd evidence is only allowed for docs-kind tickets"
    EvidenceCmdFailed = "evidence command failed to launch or exited nonzero"
    # T-0398 D-01: injected pass/fail oracle says a collected id did not pass
    EvidenceNotPassing = "Evidence id resolved but did not pass when last run"
    # T-0398 D-02: no evidence id binds to a touched/scope symbol
    EvidenceScopeUnbound = "No evidence id covers a touched/scope symbol"
    # T-0455: `frob ticket scope --add/--remove` failure modes
    ScopeChangeEmpty = "scope change requires at least one --add or --remove glob"
    ScopeChangeReasonMissing = "scope change requires a non-empty --reason"
    ScopeLeaseConflict = (
        "requested --add glob overlaps a path leased by another in-progress ticket"
    )
    ScopeRemoveNotDeclared = "requested --remove glob is not in the ticket's scope"
    ScopeRemoveOrphansEvidence = (
        "cannot remove a scope glob that already covers recorded evidence"
    )
    # T-0431: FROB_WORKTREE names a leased worktree that does not match the
    # cwd's actual git top-level -- a dispatched agent's shell wandered
    # (accidentally or otherwise) outside its assigned worktree.
    WorktreeLeaseViolation = (
        "FROB_WORKTREE is leased to a different worktree than this command's cwd"
    )


# frob:ticket T-0176
# frob:doc docs/modules/tickets.md#frob-ticket-land
class LandError(ErrorSet):
    """Fallible outcomes of `frob.tickets.land` (`frob ticket land`); every
    variant corresponds to an abort path that names its own manual remedy
    in the log line raised alongside it (T-0176)."""

    DirtyMain = "root checkout has uncommitted changes"
    NotFound = "ticket not found in the worktree's store"
    NotCloseable = "ticket is missing evidence or a Done report"
    GitFailed = "a required git operation failed"
    MergeConflict = "merging main into the worktree produced real conflicts"
    UnownedDeletions = "worktree deletes files outside the ticket's scope"
    CloseFailed = "closing the ticket after merge failed"
    SquashConflict = "squash-applying the worktree onto main produced real conflicts"
    CommitFailed = "the final landing commit failed"
    IncompleteLand = (
        "the staged squash-apply is missing file(s) the worktree changed "
        "(T-0463 completeness assertion)"
    )
    ReleaseBumpFailed = "the caller's REL001 version-bump callback failed (T-0338)"


# frob:ticket T-0176
# frob:doc docs/modules/tickets.md#frob-ticket-land
class LandReport(BaseModel):
    """Outcome of one `land()` call: what happened (or, under `dry_run`,
    what WOULD happen) landing `ticket_id` from a worktree onto main."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticket_id: str
    final_id: str
    dry_run: bool
    wip_committed: bool
    merged_main_into_worktree: bool
    ledger_spliced: bool
    unowned_deletions: tuple[str, ...] = ()
    commit_sha: str | None = None
    files_changed: tuple[str, ...] = ()
    # T-0463: the worktree's full pre-squash changeset (tracked edits,
    # untracked new files, deletions -- everything `git diff <main>...HEAD`
    # in the worktree reports once the wip-commit has made it all tracked),
    # asserted equal-or-subset of `files_changed` before the landing commit
    # is ever made. Always empty on a real (non-dry-run) success since a
    # completeness gap aborts the land instead of returning a report.
    worktree_changeset: tuple[str, ...] = ()
    # T-0338: the version `bump_version` actually applied and staged
    # (pyproject.toml + CHANGELOG.md + the release manifest), or `None` if
    # no bump was needed (or no `bump_version` callback was supplied).
    release_bumped_to: str | None = None
    # T-0338: whether `rebuild_natives` was invoked because the landed
    # changeset touched a native-extension source tree (frob-core/
    # strata-core).
    natives_rebuilt: bool = False
