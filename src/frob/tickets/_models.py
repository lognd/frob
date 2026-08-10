"""Data models and error types for frob.tickets
(docs/modules/tickets.md is authoritative)."""
# frob:waive ARCH102 reason="19 of 23 exports (after T-0977's data-only- class \
# exclusion) form one connected cluster around scope-glob matching and done-report \
# parsing over the same Ticket/Evidence models this module's docstring names; the 4 \
# outliers (is_cmd_evidence, matches_collected, unbound_acceptance, \
# render_claims_block) are small predicate/render helpers over those exact same \
# models, not a separate concern -- this is the single tickets data-model module the \
# docstring already scopes it to"
# frob:waive LARGE001 reason="T-1651: same cohesion this file's own ARCH102 waiver \
# already establishes -- one connected cluster of Ticket/Evidence data models plus the \
# scope-glob/done-report helpers over them, not a bundle of unrelated concerns. \
# Splitting by line count would cut the Ticket model's own field/validator block from \
# the helpers that operate on it, which is the opposite of a real seam."

from __future__ import annotations

import fnmatch
import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import (
    BaseModel,
    ConfigDict,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
    model_validator,
)
from typani.error_set import ErrorSet

from frob.logging import get_logger

_log = get_logger(__name__)

# frob:ticket T-1132
# T-0380 incident: `blocked_by` held an empty string alongside three real
# (done) blockers, and `doable()`'s open-blocker check treated the empty
# entry as an unresolvable id -- the ticket sat silently undoable for days
# with nothing surfacing WHY. Mirrors `frob.tickets._store._TICKET_ID_RE`'s
# shape (final `T-####` or provisional `T-draft-<8 hex>`, T-0162) -- kept
# as its own copy rather than a shared import because `_store` imports
# `Ticket` from this module at load time, so the reverse import would be
# circular; if the id-shape ever changes, update both.
_BLOCKED_BY_ID_RE = re.compile(r"^T-(?:\d{4}|draft-[0-9a-f]{8})$")


# frob:ticket T-1132
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets.py::TestIsValidTicketRef.test_accepts_final_id \
# kind="unit"
# frob:tests tests/test_tickets.py::TestIsValidTicketRef.test_accepts_draft_id \
# kind="unit"
# frob:tests tests/test_tickets.py::TestIsValidTicketRef.test_rejects_empty_string \
# kind="unit"
# frob:tests tests/test_tickets.py::TestIsValidTicketRef.test_rejects_malformed_id \
# kind="unit"
def is_valid_ticket_ref(value: str) -> bool:
    """Whether `value` is a well-formed ticket-id reference (final
    `T-####` or provisional `T-draft-<8 hex>`) -- the same check
    `Ticket`/`TicketSpec`'s `blocked_by`/`parent` field validators enforce
    at construction time (T-1132), exposed for call sites that mutate an
    EXISTING `Ticket` via `model_copy` (which bypasses pydantic field
    validators entirely, per pydantic's own documented `model_copy`
    semantics) and must therefore validate a new edge by hand before
    writing it -- see `frob.app.ticket_runner._lifecycle._block`."""
    return bool(_BLOCKED_BY_ID_RE.match(value))


def _validate_ticket_id_ref(value: str, *, field: str) -> str:
    """Reject an empty-string or malformed (non-`T-####`/`T-draft-<hex>`)
    ticket-id reference in a `blocked_by`/`parent` entry (T-1132) -- raises
    `ValueError` (pydantic wraps it into a `ValidationError`) so a
    malformed edge can never reach the ledger via `Ticket`/`TicketSpec`
    construction in the first place, closing the T-0380 class at the
    source rather than only detecting it after the fact (see `frob doctor`
    for the existing-ledger scan)."""
    if not _BLOCKED_BY_ID_RE.match(value):
        raise ValueError(
            f"{field} entry {value!r} is not a valid ticket id "
            "(expected T-#### or T-draft-<8 hex chars>)"
        )
    return value


def _validate_blocked_by(value: Sequence[str]) -> tuple[str, ...]:
    """`field_validator` body shared by `Ticket.blocked_by` and
    `TicketSpec.blocked_by` (T-1132): every entry must be a well-formed
    ticket id, empty string included as the T-0380 incident's own
    reproduction."""
    return tuple(_validate_ticket_id_ref(v, field="blocked_by") for v in value)


def _validate_parent(value: str | None) -> str | None:
    """`field_validator` body shared by `Ticket.parent` and
    `TicketSpec.parent` (T-1132): `None` (no parent) passes through
    unchanged; a present value must be a well-formed ticket id."""
    if value is None:
        return None
    return _validate_ticket_id_ref(value, field="parent")


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


# frob:ticket T-0715
# frob:doc docs/modules/tickets.md#data-models
# frob:tests tests/test_tickets_tiers.py::TestTierField.test_default_tier_is_ticket
# frob:tests tests/test_tickets_tiers.py::TestTierField.test_serialize_parse_round_trip
class TicketTier(StrEnum):
    """Where a ticket sits in the epic -> story -> ticket organization
    hierarchy (T-0715): `EPIC` parents `STORY` tickets, `STORY` parents leaf
    `TICKET` tickets, and `doable`/close enforce the shape (only `TICKET`
    tier ever surfaces as doable; an `EPIC`/`STORY` refuses to close while
    any descendant is still open). Default is `TICKET` so every pre-T-0715
    ledger row (with no `tier:` field at all) loads as a plain leaf ticket,
    unaffected."""

    EPIC = "epic"
    STORY = "story"
    TICKET = "ticket"


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
# The three targets EVERY new `frob ticket <subcommand>` structurally must
# touch to actually wire the command in: the dispatch table (`__main__.py`),
# the CLI flags it reads (`app/config.py`), and the runner that implements
# it (`app/ticket_runner/**`, a package since an earlier landing split the
# original `app/ticket_runner.py` module -- T-1163 fixed a stale
# frozenset entry here that still pointed at the pre-split single-file
# path, which could never match a real file glob and silently defeated
# this whole mechanism for the ticket_runner half of CLI wiring). T-0323
# (git-merge-driver ticket, adding `frob ticket merge-driver`) needed all
# three despite a scope declared as `src/frob/tickets/**` -- every feature
# ticket that adds a subcommand hits this same "scope-expansion ceremony"
# (a `frob ticket scope --add` per wiring file, every time) because these
# files are structurally required but never anticipated at ticket-filing
# time. Implicitly in scope for any `TicketKind.FEATURE` ticket, the same
# LEDGER_PATH-always-in-scope pattern T-0241 established for tickets.md --
# NOT extended to every kind, since a bug/docs/security ticket touching
# the CLI dispatch table unannounced is exactly the scope-creep SCOPE001
# exists to catch.
# T-1848: narrowed from the whole-package `src/frob/app/ticket_runner/**`
# glob to just the package's dispatch/re-export hub. That whole-package
# grant claimed every file under the package for ANY in-progress FEATURE
# ticket regardless of whether it ever touched CLI wiring (observed:
# T-1686 blocked T-1841's land for hours having written nothing under
# `ticket_runner/`) -- `__init__.py` is where the command families are
# re-exported/registered (see its module docstring), so it is the one
# file a new subcommand structurally touches; individual command-family
# modules (`_new.py`, `_query.py`, ...) are NOT structurally required and
# must go through an explicit `frob ticket scope --add` like any other
# file, same as `__main__.py`/`config.py` below.
CLI_WIRING_FILES = frozenset(
    {
        "src/frob/__main__.py",
        "src/frob/app/config.py",
        "src/frob/app/ticket_runner/__init__.py",
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
# frob:tests tests/test_tickets.py::TestScopeMatching.test_own_shard_always_in_scope
# frob:ticket T-1819
def scope_matches(
    path: str,
    scope: Sequence[str],
    *,
    kind: TicketKind | None = None,
    ticket_id: str | None = None,
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
    behavior unchanged.

    T-1819: when `ticket_id` is given, `tickets/<ticket_id>/**` is ALSO
    implicitly in scope -- the sharded-ledger mirror of `LEDGER_PATH`'s
    `tickets.md`-always-in-scope rule. `LEDGER_PATH` predates the sharded
    per-ticket store (`tickets/<id>/ticket.md`, `tickets/<id>/done-
    report.md`, written by routine `frob ticket start`/`sweep` auto-
    commits), so without this a ticket's own bookkeeping shard tripped a
    false SCOPE001 against its own declared scope -- the sibling gap
    T-1817 already closed for the unscoped B9 path (`frob.gates.
    _b9_exempt_file`), here closed for the per-ticket declared-scope
    check. `ticket_id=None` (the default, and every pre-T-1819 call site)
    preserves the exact prior behavior unchanged."""
    globs = _scope_globs(_split_scope_entries(scope))
    if kind is TicketKind.FEATURE:
        globs = (*globs, *CLI_WIRING_FILES)
    if ticket_id is not None:
        globs = (*globs, f"tickets/{ticket_id}/**")
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
# frob:tests \
# tests/test_tickets_lease.py::TestGlobsIntersect.test_wildcard_prefix_overlaps_literal
# frob:tests \
# tests/test_tickets_lease.py::TestGlobsIntersect.test_disjoint_literal_siblings
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


# frob:ticket T-0572
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_acceptance.py::TestUnboundAcceptance.test_empty_acceptance_list_is_never_unbound  # noqa: E501
def unbound_acceptance(ticket: Ticket) -> tuple[AcceptanceCriterion, ...]:
    """Acceptance criteria on `ticket` with no evidence id that both (a) the
    criterion itself lists and (b) still resolves against `ticket.evidence`
    -- the T-0572 close gate this feeds. A criterion whose evidence id was
    bound but later dropped from `ticket.evidence` (e.g. a scope --remove
    that orphaned it) is treated as unbound again, not grandfathered: the
    binding must hold NOW, not merely have been recorded once. An empty
    `ticket.acceptance` (no criteria declared at all) always returns `()`
    -- the T-0572 backward-compat rule that a ticket with no acceptance
    list closes exactly as it did before this feature existed."""
    evidence_set = set(ticket.evidence)
    return tuple(
        c for c in ticket.acceptance if not any(e in evidence_set for e in c.evidence)
    )


# frob:doc docs/modules/tickets.md#public-api
# T-0458: public (no leading underscore) so `frob.tickets.compose_done_report`
# can reuse the SAME heading string `has_substantive_done_report`/
# `replace_done_report_section` key off, rather than a second hand-typed
# copy that could silently drift out of sync with what the D-03 check
# recognizes as a real Done-report heading.
DONE_REPORT_HEADING = "## Done report"
_DONE_REPORT_HEADING = DONE_REPORT_HEADING

# frob:ticket T-0848
# The only `## ` headings ever written into a ticket body PROGRAMMATICALLY
# by code in this package, besides `DONE_REPORT_HEADING` itself -- i.e. the
# complete set of genuine structural section boundaries a Done-report
# section can legitimately end at. `frob.tickets._append_to_section`
# (`__init__.py`) writes `## Failure log` / `## Drop reason` entries, and
# both import this set (rather than each defining its own private copy)
# so the two can never drift apart (NO DUPLICATION). A `## ` line that is
# NOT one of these -- e.g. an author's own `## Per-pattern decision` or
# `## Evidence` sub-heading inside the narrative text passed via
# `--why-file` -- is part of the Done-report BODY, not a new section, and
# must not terminate the scan (T-0848: doing so is exactly what let a
# second `done-report` call duplicate the entire prior narrative instead
# of replacing it).
# frob:doc docs/modules/tickets.md#public-api
FAILURE_LOG_HEADING = "## Failure log"
# frob:doc docs/modules/tickets.md#public-api
DROP_REASON_HEADING = "## Drop reason"
_STRUCTURAL_HEADINGS_AFTER_DONE_REPORT = frozenset(
    {FAILURE_LOG_HEADING, DROP_REASON_HEADING}
)
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
# frob:ticket T-0848
# frob:tests tests/test_evidence_integrity.py::TestDoneReportSectionEndStructuralSentinel.test_narrative_h2_subheadings_do_not_end_the_section  # noqa: E501
def _done_report_section_end(lines: list[str], heading_idx: int) -> int:
    """The index one past the END of the `## Done report` section starting
    at `heading_idx`: the next STRUCTURAL `## ` heading (another
    `## Done report`, `## Failure log`, or `## Drop reason` -- the fixed
    set this package ever writes programmatically past a Done report,
    `_STRUCTURAL_HEADINGS_AFTER_DONE_REPORT`), or `len(lines)`.

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
    section, so a stray duplicate self-heals the next time either runs.

    T-0848: a naive "stop at ANY `## ` line" boundary (the pre-fix shape)
    breaks the moment the Done-report NARRATIVE ITSELF legitimately uses
    `## ` sub-headings (e.g. `## Per-pattern decision`, `## Evidence`) --
    the scan used to stop at the FIRST such line, so a second
    `done-report --why-file` call only ever overwrote the short intro
    before it, leaving the entire stale prior report (including any
    factual claim a later round disproved) to survive verbatim just past
    the new one. Only a heading from the fixed structural set now ends
    the section; any other `## ` line is narrative content the caller
    wrote on purpose and stays inside the replaceable window."""
    end_idx = len(lines)
    for i in range(heading_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped == _DONE_REPORT_HEADING:
            continue
        if stripped in _STRUCTURAL_HEADINGS_AFTER_DONE_REPORT:
            end_idx = i
            break
    return end_idx


# frob:ticket T-0853
# frob:tests tests/test_evidence_integrity.py::TestDoneReportHeadingImpersonation.test_lookalike_heading_without_changed_marker_not_real  # noqa: E501
def _is_real_done_report_heading(lines: list[str], heading_idx: int) -> bool:
    """Whether the `## Done report`-matching line at `heading_idx` begins a
    GENUINE section rather than mere narrative that happens to read
    identically (T-0853): a line-wrapped quoted phrase inside a `--why-file`
    narrative (or a hand-authored Description/Plan section discussing this
    very class of bug) can put the literal heading text at the start of its
    own physical line, which is byte-for-byte indistinguishable from a real
    (possibly stray/placeholder) heading by exact-string match alone.

    A genuine `## ` (H2) Markdown heading is always either the very first
    line of the body or preceded by a blank line -- every site in this
    package that WRITES a `## Done report` heading (`replace_done_report_
    section`'s append branch, `compose_done_report`'s `f"{DONE_REPORT_
    HEADING}\\n\\n..."` shape) follows this convention, and hand-authored
    ticket prose (Description/Plan, via `ticket new --body-file`) is
    Markdown too, so a real section heading respects it as well. A
    heading-lookalike line produced by mid-paragraph line-wrap, by
    contrast, is immediately preceded by ANOTHER TEXT LINE continuing the
    same paragraph -- never a blank line -- which is exactly what this
    check rejects, without requiring anything about what follows the
    candidate line (unlike an earlier draft of this fix that required a
    trailing `### Changed` marker and broke every legitimately terse Done
    report, e.g. this repo's own `## Done report\\nDone.` test fixtures,
    which never render a Changed/Evidence block at all)."""
    return heading_idx == 0 or lines[heading_idx - 1].strip() == ""


# frob:ticket T-0853
# frob:tests tests/test_evidence_integrity.py::TestDoneReportHeadingImpersonation.test_lookalike_heading_before_real_report_ignored  # noqa: E501
def _find_done_report_heading(lines: list[str]) -> int | None:
    """Index of the first line that begins a GENUINE `## Done report`
    section, or `None` if no such heading exists (T-0853).

    Scans every line equal to `_DONE_REPORT_HEADING` in order, skipping any
    match `_is_real_done_report_heading` rejects (a narrative line that
    merely reads identically to the heading, never an actual section
    start) -- so a heading-lookalike line anywhere in the body (most
    commonly BEFORE the real heading, in hand-authored Description/Plan
    prose describing this very class of bug) can never be mistaken for the
    real section boundary that `_done_report_section_lines`/
    `replace_done_report_section` splice against."""
    for i, line in enumerate(lines):
        if line.strip() == _DONE_REPORT_HEADING and _is_real_done_report_heading(
            lines, i
        ):
            return i
    return None


def _done_report_section_lines(body: str) -> list[str] | None:
    """The raw lines of body's `## Done report` section (up to the next
    non-Done-report `## ` heading or EOF, T-0493), or `None` if no such
    heading exists."""
    lines = body.splitlines()
    heading_idx = _find_done_report_heading(lines)
    if heading_idx is None:
        return None
    end_idx = _done_report_section_end(lines, heading_idx)
    return lines[heading_idx + 1 : end_idx]


# frob:ticket T-1005
# The literal marker `compose_done_report` always writes right after the
# narrative (`f"{why_text}\n\n### Changed\n..."`) -- the SAME fixed string
# `_capture_done_report_claims`/`_CLAIMS_HEADING`'s neighbors already rely
# on as a structural anchor, reused here as `recover_done_report_why`'s own
# anchor rather than inventing a second convention.
_CHANGED_HEADING = "### Changed"


# frob:ticket T-1005
# frob:doc docs/modules/tickets.md#public-api
# frob:tests \
# tests/test_ticket_reverify.py::TestRecoverDoneReportWhy.test_recovers_narrative_befor\
# e_changed_marker
# frob:tests \
# tests/test_ticket_reverify.py::TestRecoverDoneReportWhy.test_none_when_no_done_report\
# _section
# frob:tests \
# tests/test_ticket_reverify.py::TestRecoverDoneReportWhy.test_none_when_no_changed_mar\
# ker_to_anchor_against
def recover_done_report_why(body: str) -> str | None:
    """Recover the free-narrative WHY prose a caller once passed to
    `set_done_report`/`compose_done_report`, given only the ticket `body`
    that resulted -- the mechanical inverse of `compose_done_report`'s own
    `why_text` half. `frob ticket reverify` (T-1005) uses this to refresh a
    DONE ticket's recap (a fresh `set_done_report` call) without asking the
    operator to retype a narrative that already exists verbatim in the
    ledger.

    Returns `None` (never an empty string) if there is no Done report
    section at all, or if the section has no auto-filled `### Changed`
    marker to anchor against (an old/terse Done report predating T-0458's
    auto-fill sections -- this repo's own `## Done report\\nDone.`-shaped
    test fixtures) -- callers must treat `None` as "no narrative to
    replay," never silently fall back to composing a fresh
    `(no narrative supplied)` report over a real one."""
    section = _done_report_section_lines(body)
    if section is None:
        return None
    changed_idx = next(
        (i for i, line in enumerate(section) if line.strip() == _CHANGED_HEADING),
        None,
    )
    if changed_idx is None:
        return None
    why_text = "\n".join(section[:changed_idx]).strip()
    return why_text or None


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


# frob:ticket T-0754
_CLAIMS_HEADING = "### Captured claims"

# frob:ticket T-0754
# The `### Captured claims` section's exact rendered line shapes -- single
# source of truth for both `render_claims_block` (write) and
# `parse_claims_from_done_report` (read), so the two can never drift apart
# the way free-prose test/gate claims used to (T-0754's whole point).
#
# T-0754 review round 2 (FATAL fix): the gate line is now three plain
# integers (errors/warnings/waived), NEVER the free-text `frob check`
# summary line -- that line's own trailing `[archgate=7.99s, ...]` timing
# blob is different on every single invocation of an IDENTICAL tree (wall
# time, not content), so a strict-equality re-verification against it
# refused EVERY land, including this ticket's own. Structured integers
# have no such nondeterministic tail.
_CLAIMS_TESTS_RE = re.compile(
    r"^- tests: (\d+) passed \(from (\d+) evidence id\(s\)\)$"
)
_CLAIMS_GATES_RE = re.compile(
    r"^- gates: (\d+) error\(s\), (\d+) warning\(s\), (\d+) waived$"
)

# frob:ticket T-0832
# T-0832: the exact rendered marker for an UNMEASURED gate-state claim -- a
# fresh `frob check --ticket` that produced no parsable gate-summary at
# done-report time (missing lease, crash, unparsable output). Recognized on
# parse so an unmeasured claim reads as "no gate-state recorded" rather than
# "no Captured claims section at all," which would also drop the (separately
# measurable) test-count claim on the floor. Never a negative sentinel: a
# real `frob check` run can never produce negative counts, so a stored -1
# used to compare as vacuously equal to another unmeasured -1 (the T-0830
# incident this closes) -- this marker instead has no numeric value at all.
_CLAIMS_GATES_UNMEASURED = (
    "- gates: unmeasured (no parsable gate-summary from a fresh check)"
)

# frob:ticket T-0846
# T-0846: the rendered marker for a captured claim whose error IDENTITY set
# (rule id + file, alongside the plain count) was measured but happened to
# be empty -- distinct from the line being absent entirely (which means no
# identity-level capture was supplied at all, e.g. an old Done report or a
# caller that only ever passed `check_gates`). Never omit the line when the
# set is genuinely empty: an absent line and an empty-but-measured set mean
# different things to `_reverify_done_report_claims_post_merge` (identity
# compare vs count-only fallback).
_CLAIMS_ERROR_FINDINGS_NONE = "- error-findings: none (measured, zero errors)"
_CLAIMS_ERROR_FINDINGS_RE = re.compile(r"^- error-findings: (.+)$")


# frob:ticket T-0754
# frob:ticket T-0832
# frob:ticket T-0846
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel.test_error_findings_round_trips_through_a_done_report_body kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel.test_measured_empty_error_findings_differs_from_none kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_masked_self_introduced_error_in_own_scope_still_refuses_via_identity kind="integration"  # noqa: E501
class DoneReportClaims(BaseModel):
    """Structured, CAPTURED (never hand-typed) Done-report claims (T-0754):
    `test_count` is the number of a ticket's non-cmd evidence ids observed
    ACTUALLY PASSING by a real run at done-report time (not retyped from
    memory or a stale run -- the root cause of the T-0572/T-0710/T-0724
    incidents this closes), `evidence_count` is how many non-cmd evidence
    ids that run was measured against (so a later divergence can tell
    "fewer passed" from "the evidence set itself changed"), and
    `gate_errors`/`gate_warnings`/`gate_waived` are a fresh `frob check
    --ticket` run's own error/warning/waived COUNTS -- deliberately never
    that run's free-text summary line, whose trailing per-gate timing blob
    is nondeterministic even against an unchanged tree (T-0754 review
    round 2). `land` re-captures all of these against the post-merge tree
    and errors if the test claim or `gate_errors` no longer match
    (`_land.py`'s `_reverify_done_report_claims_post_merge`); `gate_
    warnings`/`gate_waived` are recorded for a human reader but NOT
    compared at land -- repo-global warning/waived counts legitimately
    move on a busy shared branch for reasons that have nothing to do with
    this ticket's own work, so gating on them would produce the same
    false-refusal class this round's fix closes for timing.

    T-0832: `gate_errors`/`gate_warnings`/`gate_waived` are `int | None` --
    `None` means UNMEASURED (the fresh `frob check --ticket` that would
    have produced them found no parsable gate-summary, e.g. because the
    ticket held no lease at capture time), never a `-1` sentinel. A `-1`
    sentinel compares equal to another later `-1` sentinel, which let a
    land's re-verification pass vacuously exactly when it could least
    measure anything (the T-0830 incident); `None` cannot silently compare
    equal to a real integer, so callers are forced to branch on
    "unmeasured" explicitly instead of accidentally trusting it. The test-
    count fields stay required (`int`, never `None`) -- they are always
    measurable whenever `run_tests`/`passing_ids` themselves ran at all,
    unlike the gate state, which depends on a live `frob check` subprocess
    that can fail for reasons unrelated to the ticket's own evidence.

    T-0846: `error_findings` is an OPTIONAL `frozenset[(rule_id, file)]`
    alongside the plain `gate_errors` count -- a scope-wide count alone let
    a land whose own diff introduced N new errors sail through whenever an
    UNRELATED fix on the same branch removed more than N (a self-introduced
    regression laundered by a net-better total; the reviewer-flagged gap in
    the count-only `>` fix). `None` means no identity-level capture was
    supplied (an old Done report, or a caller that only ever passed
    `check_gates`) -- `_reverify_done_report_claims_post_merge` falls back
    to the count-only `>` comparison in that case; a real (possibly empty)
    frozenset means the identity-diff comparison is authoritative instead."""

    model_config = {}

    test_count: int
    evidence_count: int
    gate_errors: int | None
    gate_warnings: int | None
    gate_waived: int | None
    error_findings: frozenset[tuple[str, str]] | None = None


# frob:ticket T-0754
# frob:ticket T-0832
# frob:ticket T-0846
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel.test_round_trips_through_a_done_report_body kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel.test_error_findings_round_trips_through_a_done_report_body kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel.test_measured_empty_error_findings_differs_from_none kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_two_unmeasured_gate_claims_never_vacuously_match kind="integration"  # noqa: E501
def render_claims_block(claims: DoneReportClaims) -> str:
    """Render `claims` as a Done report `### Captured claims` section
    (T-0754) -- the mechanical inverse of `parse_claims_from_done_report`,
    matching `_CLAIMS_TESTS_RE`/`_CLAIMS_GATES_RE` (or, T-0832, the literal
    `_CLAIMS_GATES_UNMEASURED` marker when `claims.gate_errors is None`)
    exactly so a round-trip through a written ledger never loses precision
    -- and, T-0832, never renders a negative gate count: an unmeasured gate
    state renders as the explicit `unmeasured` marker line instead.

    T-0846: an `error_findings` set (when not `None`) renders as its own
    trailing line, sorted for a deterministic round-trip -- `rule@file`
    pairs, comma-joined, or the `_CLAIMS_ERROR_FINDINGS_NONE` marker when
    the set is measured but empty. `None` (no identity capture supplied)
    omits the line entirely, matching the T-0832 unmeasured-gates
    precedent: absence and "measured empty" must render differently."""
    gates_line = (
        _CLAIMS_GATES_UNMEASURED
        if claims.gate_errors is None
        else (
            f"- gates: {claims.gate_errors} error(s), {claims.gate_warnings} "
            f"warning(s), {claims.gate_waived} waived"
        )
    )
    lines = [
        _CLAIMS_HEADING,
        f"- tests: {claims.test_count} passed "
        f"(from {claims.evidence_count} evidence id(s))",
        gates_line,
    ]
    if claims.error_findings is not None:
        if claims.error_findings:
            joined = ", ".join(
                f"{rule}@{file}" for rule, file in sorted(claims.error_findings)
            )
            lines.append(f"- error-findings: {joined}")
        else:
            lines.append(_CLAIMS_ERROR_FINDINGS_NONE)
    return "\n".join(lines)


# frob:ticket T-0754
# frob:ticket T-0832
# frob:ticket T-0846
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel.test_round_trips_through_a_done_report_body kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel.test_missing_section_returns_none kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel.test_free_prose_elsewhere_never_masquerades_as_claims kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel.test_error_findings_round_trips_through_a_done_report_body kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel.test_measured_empty_error_findings_differs_from_none kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_two_unmeasured_gate_claims_never_vacuously_match kind="integration"  # noqa: E501
def parse_claims_from_done_report(body: str) -> DoneReportClaims | None:
    """Recover a `### Captured claims` section from `body`'s `## Done
    report`, the inverse of `render_claims_block` (T-0754). Returns `None`
    if no such section is present (a Done report written before T-0754, or
    by a caller that opted the capture callables out) -- callers treat
    `None` as "nothing to re-verify," never as a hard failure, since older
    tickets must still be landable.

    T-0754 review round 2 (security fix): ANCHORED to the `### Captured
    claims` heading itself -- only lines strictly between that heading and
    the next `#`-prefixed heading (or the section's end) are matched
    against `_CLAIMS_TESTS_RE`/`_CLAIMS_GATES_RE`. Scanning the WHOLE Done
    report (the pre-review-round-2 shape) let a free-prose narrative line
    that happened to match either regex's shape masquerade as a captured,
    re-verified claim -- exactly the "unverified free prose" hole T-0754
    exists to close, just moved one level down."""
    section = _done_report_section_lines(body)
    if section is None:
        return None
    claims_lines = _extract_claims_section_lines(section)
    if claims_lines is None:
        return None
    return _parse_claims_lines(claims_lines)


# frob:ticket T-0976
def _extract_claims_section_lines(section: list[str]) -> list[str] | None:
    """The lines strictly between the `### Captured claims` heading and
    the next `#`-prefixed heading (or the section's end) within `section`
    -- `parse_claims_from_done_report`'s heading-anchoring half (T-0754
    review round 2's security fix), split from its line-parsing half.
    `None` if the heading is not present at all."""
    claims_idx = next(
        (i for i, line in enumerate(section) if line.strip() == _CLAIMS_HEADING), None
    )
    if claims_idx is None:
        return None
    claims_lines: list[str] = []
    for line in section[claims_idx + 1 :]:
        if line.strip().startswith("#"):
            break
        claims_lines.append(line)
    return claims_lines


# frob:ticket T-0976
def _parse_claims_lines(claims_lines: list[str]) -> DoneReportClaims | None:
    """Parse the anchored `claims_lines` (already isolated from the rest
    of the Done report by `_extract_claims_section_lines`) into a
    `DoneReportClaims`, or `None` if the test-count fields (the only ones
    required, T-0832) never matched -- `parse_claims_from_done_report`'s
    line-parsing half."""
    test_count = evidence_count = None
    gate_errors = gate_warnings = gate_waived = None
    error_findings: frozenset[tuple[str, str]] | None = None
    for line in claims_lines:
        stripped = line.strip()
        tests_match = _CLAIMS_TESTS_RE.match(stripped)
        if tests_match:
            test_count, evidence_count = (int(g) for g in tests_match.groups())
            continue
        gates_match = _CLAIMS_GATES_RE.match(stripped)
        if gates_match:
            gate_errors, gate_warnings, gate_waived = (
                int(g) for g in gates_match.groups()
            )
            continue
        if stripped == _CLAIMS_ERROR_FINDINGS_NONE:
            error_findings = frozenset()
            continue
        findings_match = _CLAIMS_ERROR_FINDINGS_RE.match(stripped)
        if findings_match:
            pairs = set()
            for token in findings_match.group(1).split(", "):
                rule, _, file = token.partition("@")
                if rule and file:
                    pairs.add((rule, file))
            error_findings = frozenset(pairs)
            continue
        # T-0832: the explicit "unmeasured" marker is recognized (so it
        # does not fall through as an unparsed leftover line) but leaves
        # gate_errors/warnings/waived at their None default -- there is no
        # numeric value to recover, by design.
    # T-0832: only the test-count fields are required for a claims section
    # to exist at all -- gate_errors/warnings/waived may legitimately be
    # None (unmeasured at capture time) while the test claim is still a
    # real, measured value worth re-verifying at land.
    if test_count is None or evidence_count is None:
        return None
    return DoneReportClaims(
        test_count=test_count,
        evidence_count=evidence_count,
        gate_errors=gate_errors,
        gate_warnings=gate_warnings,
        gate_waived=gate_waived,
        error_findings=error_findings,
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

    T-0853: heading detection is delegated to `_find_done_report_heading`,
    which skips any line that merely READS like the heading (a line-wrapped
    quoted phrase inside a narrative, with no `### Changed` marker ahead of
    it) rather than treating the first exact text match anywhere in `body`
    as the section start -- otherwise a heading-lookalike line sitting in
    the ticket's pre-existing Description/Plan prose (written before any
    real Done report exists) gets mistaken for the boundary, and everything
    that followed it in the body is silently dropped on splice.
    """
    lines = body.splitlines()
    heading_idx = _find_done_report_heading(lines)
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


# frob:ticket T-0572
# frob:doc docs/modules/tickets.md#data-models
class AcceptanceCriterion(BaseModel):
    """One given/when/then acceptance item bound to the evidence id(s) that
    demonstrate it (T-0572): `evidence` empty means the criterion is not
    yet mapped to anything and blocks `done` (see `_unbound_acceptance`).
    Ids here are expected to also appear in the owning `Ticket.evidence`
    (bound via `bind_acceptance`/`--accepts`), not a free-standing list --
    close only trusts evidence it can itself resolve."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    evidence: tuple[str, ...] = ()

    @field_validator("evidence", mode="before")
    @classmethod
    def _normalize_evidence(cls, value: Sequence[str]) -> tuple[str, ...]:
        """Split any comma-joined entry the same way `Ticket.scope`/`labels`
        do (T-0241 precedent), so a hand-typed `--evidence 'a,b'` still
        binds both ids."""
        return _split_scope_entries(value)


def _coerce_acceptance(value: Sequence[object]) -> list[dict | object]:
    """Accept either the legacy plain-string acceptance list (pre-T-0572
    ledgers: `acceptance: [text, text, ...]`) or the new structured
    `{text, evidence}` mapping form, normalizing the legacy shape to the
    structured one so `Ticket`/`TicketSpec` validate either without the
    caller needing to know which era wrote them. A ticket already on disk
    with plain-string criteria keeps loading and displaying exactly as
    before; it simply reads as unbound (empty `evidence`) until someone
    binds it, which is the correct default -- backward compat is about
    never failing to LOAD, not about grandfathering unmapped criteria past
    the new close gate."""
    coerced: list[dict | object] = []
    for item in value:
        if isinstance(item, str):
            coerced.append({"text": item, "evidence": ()})
        else:
            coerced.append(item)
    return coerced


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


# frob:ticket T-1422
# frob:doc docs/modules/tickets.md#data-models
class AcceptanceAmendmentOp(StrEnum):
    """Whether an `acceptance_amendments` audit entry replaced a criterion's
    text (T-1422) or removed it outright."""

    REPLACE = "replace"
    REMOVE = "remove"


# frob:ticket T-1422
# frob:doc docs/modules/tickets.md#data-models
class AcceptanceAmendmentEntry(BaseModel):
    """One append-only audit line for a `frob ticket accept --amend/--remove`
    mutation (T-1422): the `frob ticket scope`/`ScopeChangeEntry` discipline
    (T-0455) applied to acceptance criteria -- what index moved, which
    direction, the OLD text (always recorded, even for a replace, so a
    reviewer can see exactly what was overwritten), the NEW text (`None`
    for a remove), why, who, and when. Never edited or removed once
    written, only appended to.

    The `reason` field is the entire point of this verb existing at all: an
    amendment with no reason is indistinguishable from silently rewriting
    history, which is exactly the hand-edit-the-ledger workaround this
    ticket replaces. Amending is a legitimate correction when the criterion
    was WRONG (mis-specified); it is goalpost-moving when the criterion was
    RIGHT and the work fell short. This model cannot tell those two apart
    -- only a human or reviewer reading `reason` against the diff can --
    so it makes the change reviewable (mandatory reason, surfaced in `frob
    ticket show` and the Done report) instead of pretending to adjudicate
    it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    op: AcceptanceAmendmentOp
    index: int
    old_text: str
    new_text: str | None = None
    reason: str
    actor: str
    at: date


# frob:ticket T-1733
# frob:doc docs/modules/gates.md#public-api
class EvidenceChangeEntry(BaseModel):
    """One append-only audit line for a `frob ticket evidence --replace`
    mutation (T-1733): the `ScopeChangeEntry`/`AcceptanceAmendmentEntry`
    discipline (T-0455/T-1422) applied to evidence -- what old node id
    was rebound to what new one, why, who, and when. Never edited or
    removed once written, only appended to.

    Closes the asymmetry T-1733 exists to fix: `frob ticket scope`
    already REQUIRES `--reason` for any scope change and records it here
    (`ScopeChangeEntry`); `frob ticket evidence --replace` -- the only
    verb that can shrink or weaken what proves a ticket, since a pure
    `add_evidence` append is unaffected -- required nothing at all and
    recorded nothing. An agent facing a slow close could silently
    unbind its strongest (and slowest) evidence via `--replace` with no
    trace in the ledger; this entry is the trace. `reason` is mandatory
    (`replace_evidence` refuses with `EvidenceReplaceReasonMissing`
    otherwise) for the same reason `AcceptanceAmendmentEntry.reason` is:
    a rebind with no stated reason is indistinguishable from quietly
    discarding the strongest evidence to force a close."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    old_node: str
    new_node: str
    reason: str
    actor: str
    at: date


# frob:ticket T-1749
# frob:doc docs/modules/gates.md#public-api
class DesignatedReproChangeEntry(BaseModel):
    """One append-only audit line for a `frob ticket evidence
    --designate-repro` REDESIGNATION (T-1749): who retargeted BUG002's
    repro check away from a previously-designated id, to what, when, and
    (optionally) why.

    T-1733 found and fixed the identical shape of gap for
    `--replace` (see `EvidenceChangeEntry`); T-1749 found a second
    instance in `--designate-repro`: it can silently redirect BUG002's
    FAIL-at-parent check onto a different already-bound id with no trace
    in the ledger. Narrower than the `--replace` gap in one respect
    (`set_designated_repro_test` already refuses a target that is not one
    of the ticket's own bound evidence ids -- it cannot invent an
    unverified id), so `reason` here is OPTIONAL, not required: a
    FIRST-time designation on a fresh ticket (`old_value is None`) is
    closer to pure addition and records no entry at all (mirroring
    `replace_evidence`'s own old==new no-op-is-not-an-audit-event
    posture); only a REdesignation (an already-set value being changed to
    a different one) appends here, `reason=None` when the caller did not
    supply one -- CLI enforcement of a REQUIRED reason on redesignation is
    follow-up work (see this ticket's own Done report) that needs
    `src/frob/_cli_parsers/**`/`src/frob/app/config.py` wiring outside
    this ticket's declared scope; this model exists so that follow-up has
    real data to consume rather than inventing the field itself."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    old_value: str | None
    new_value: str
    reason: str | None
    actor: str
    at: date


# frob:ticket T-0571
# frob:doc docs/modules/tickets.md#data-models
class ReviewVerdict(StrEnum):
    """The outcome an adversarial reviewer records for one review pass
    (T-0571): `approve` or `reject`, never a silent third option."""

    APPROVE = "approve"
    REJECT = "reject"


# frob:ticket T-0571
# frob:doc docs/modules/tickets.md#data-models
class ReviewEntry(BaseModel):
    """One append-only structured review record (T-0571): who reviewed,
    what they decided, a findings summary, the commit they reviewed, and
    when. This is the FIRST-CLASS EVIDENCE channel adversarial review was
    missing -- before this, a reviewer's APPROVE/REJECT verdict lived only
    in dispatch-chat prose, invisible to `frob ticket close`. Never edited
    or removed once written, only appended to (same discipline as
    `ScopeChangeEntry`/`FailureEntry`)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    verdict: ReviewVerdict
    reviewer: str
    findings: str
    commit: str
    at: date


# frob:ticket T-0838
# frob:tests tests/test_tickets.py::TestEmptyCollectionOmission.test_dict_without_empty_collections_returned_unchanged  # noqa: E501
def _omit_empty_collections(data: Mapping[str, object]) -> dict[str, object]:
    """Drop every key of `data` whose value is an empty `list`/`tuple` (T-0838).

    THE single implementation `Ticket._omit_empty_collections_on_dump` (and
    any future ledger-block model needing the same treatment) delegates to,
    so "what counts as omittable" can never desync between two hand-written
    copies. Additive collection fields (e.g. `reviews`) default to an empty
    tuple -- writing that default out as `reviews: []` on every ticket that
    has never used the feature is exactly the noise this closes: an older
    frob reading a newer ledger never needs to see a field it never
    populated. Deliberately NOT applied to scalar/`None` fields (`parent:
    null`, `threat: null`, ...) -- those already round-trip fine today and
    doing so is out of this ticket's stated scope (empty COLLECTIONS only).
    """
    return {
        key: value
        for key, value in data.items()
        if not (isinstance(value, (list, tuple)) and len(value) == 0)
    }


# frob:doc docs/modules/tickets.md#data-models
# frob:ticket T-1733
# frob:waive AFFECT001 reason="T-1733: Ticket's affects()-closure doc \
# (docs/modules/tickets.md#data-models) genuinely needs the new evidence_changes field \
# documented -- but docs/modules/tickets.md is leased by another in-progress agent \
# (T-1715/T-1739) for the duration of this ticket's work, so touching it here would \
# collide with that lease. EvidenceChangeEntry/evidence_changes are documented in full \
# in this ticket's own docs home instead (docs/modules/gates.md's new 'TEST018 \
# (T-1733)' section); remove this waiver once the tickets.md lease clears and its own \
# data-models entry can be added"
class Ticket(BaseModel):
    """One ticket: frontmatter fields plus the verbatim markdown body.

    T-0838: `extra="allow"` (not `extra="forbid"`) is a deliberate FORWARD-
    COMPATIBILITY relaxation -- a ledger written by a NEWER frob binary that
    has added a field this binary's `Ticket` does not know about (e.g.
    T-0571's `reviews`, before this model knew about it) must load, not hard
    -fail `MalformedFrontmatter`. Unknown keys land in `__pydantic_extra__`
    (pydantic's own capture mechanism), are logged at WARNING by
    `_warn_unknown_extras` naming the field(s) and the likely cause, and are
    re-emitted verbatim on the next `model_dump` (pydantic includes
    `__pydantic_extra__` in serialization automatically) -- so an OLDER
    binary landing a NEWER worktree's ledger preserves data it cannot itself
    interpret, instead of silently stripping it. Validation stays STRICT for
    every KNOWN field: `extra="allow"` only widens what is TOLERATED, it
    does not loosen a single type/enum check on a field this model already
    declares."""

    model_config = ConfigDict(frozen=True, extra="allow")

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
    # frob:ticket T-0715
    # where this ticket sits in the epic -> story -> ticket hierarchy;
    # defaults to TICKET (a plain leaf) so every pre-T-0715 ledger row
    # loads unaffected. Structural rules live in `frob.tickets.doable`
    # (leaf-only) and `_done_transition_guard` (no closing over an open
    # descendant).
    tier: TicketTier = TicketTier.TICKET
    # frob:ticket T-0715
    # free-form sprint label (e.g. "2026-W30", "sprint-14") a ticket is
    # committed to; `None` means uncommitted/backlog. Settable at
    # creation or via `frob ticket sprint assign`.
    sprint: str | None = None
    # frob:ticket T-1613
    # runs-last marker (T-1613): when True, this ticket stays structurally
    # UNDOABLE (`doable` never returns it, `start` refuses it) while ANY
    # OTHER ticket in the ledger is non-terminal (state not in
    # {done, dropped} -- `_OPEN_STATES`'s own definition, chosen over
    # "only in-progress" because a queued ticket someone starts a minute
    # later is the identical hazard, just deferred). Two or more runs-last
    # tickets are allowed simultaneously and order among THEMSELVES via
    # ordinary `blocked_by` edges -- the runs-last check only counts
    # OTHER, non-runs-last tickets, so it never becomes a mutual deadlock
    # between runs-last siblings. Distinct from `blocked_by` (a fixed,
    # enumerable edge set fixed at filing time): runs-last is dynamic --
    # it re-evaluates against whatever tickets exist NOW, including ones
    # filed after this ticket was. `frob ticket new --runs-last` warns
    # loudly if a runs-last ticket is currently IN_PROGRESS, since filing
    # new ordinary work invalidates the precondition it started under.
    runs_last: bool = False
    scope: tuple[str, ...] = ()
    # frob:ticket T-1484
    # honest acknowledged-broad escape hatch for TICK009 (WAVE14-B): when
    # True, `_tick009_scope_breadth_nudges` skips this ticket entirely,
    # regardless of `tier` -- an epic/umbrella ticket's scope is
    # DELIBERATELY broad (it tracks a whole campaign, not one file list),
    # and TICK009 previously had no waive channel at all (`frob:waive`
    # only suppresses one violation LINE, and TICK009 is not in
    # `_UNWAIVABLE_RULES` but still fired a fresh nudge every ledger-wide
    # scan since the acknowledgement had nowhere to persist). Set via
    # `frob ticket scope-ack <id> --reason TEXT`, never by hand-editing
    # the ledger -- `scope_breadth_ack_reason` records WHY, so an
    # acknowledgement is never silent the way a missing waiver reason
    # would be.
    scope_breadth_ack: bool = False
    # frob:ticket T-1484
    # required human-readable justification for `scope_breadth_ack=True`;
    # `None` when `scope_breadth_ack` is False. Set together by
    # `set_scope_breadth_ack`, never independently.
    scope_breadth_ack_reason: str | None = None
    # frob:ticket T-0455
    # append-only audit trail of every `frob ticket scope --add/--remove`
    # mutation this ticket's `scope` has gone through (never edited, only
    # appended) -- makes scope creep visible instead of a silent SCOPE001
    # waive.
    scope_changes: tuple[ScopeChangeEntry, ...] = ()
    evidence: tuple[str, ...] = ()
    # frob:ticket T-1616
    # append-only audit trail of every `frob ticket kind` change made
    # AFTER this ticket already carried evidence and/or a substantive
    # Done report -- makes a post-hoc reclassification (e.g. bug -> feature
    # to dodge BUG002, T-1616) visible in the ledger and at land time
    # instead of a silent frontmatter edit. A kind change on a fresh
    # ticket (no evidence, no Done report yet) is ordinary and does NOT
    # append here -- only a change that could plausibly be relaxing an
    # already-earned evidence obligation.
    kind_history: tuple[str, ...] = ()
    # frob:ticket T-1670
    # the pytest-node-id evidence entry BUG002 re-runs at the parent commit,
    # set explicitly via `frob ticket evidence <id> --designate-repro` (or
    # `None` to fall back to `_designated_repro_test`'s positional-first-
    # match default). Before this field existed, BUG002 always took the
    # FIRST pytest-node-id in `evidence` regardless of which one an agent
    # actually intended as the repro -- an invisible bind-ORDER dependency
    # (T-1652/T-1653/T-1635 all hit it: a pre-existing test bound first,
    # the real new repro test bound second, so BUG002 checked the WRONG
    # test and refused land). Explicit designation makes the choice a
    # value, not an inferred position.
    designated_repro_test: str | None = None
    # frob:ticket T-1749
    # append-only audit trail of every REDESIGNATION (not first-time
    # designation) of `designated_repro_test` -- the EvidenceChangeEntry
    # discipline applied to the OTHER silent BUG002-check-redirect T-1733's
    # audit pass found: `--designate-repro` can retarget BUG002's check
    # onto a weaker already-bound id with no trace unless this records it.
    designated_repro_changes: tuple[DesignatedReproChangeEntry, ...] = ()
    # frob:ticket T-0571
    # append-only structured adversarial-review records (`frob ticket
    # review`), each naming the commit reviewed -- `close --strict` (T-0571)
    # requires at least one `verdict: approve` entry naming the CURRENT
    # final commit before it will transition to done.
    reviews: tuple[ReviewEntry, ...] = ()
    attachments: tuple[Attachment, ...] = ()
    # given/when/then acceptance criteria the reviewer verifies (T-0006),
    # each bound to the evidence id(s) that demonstrate it (T-0572)
    acceptance: tuple[AcceptanceCriterion, ...] = ()
    # frob:ticket T-1422
    # append-only audit trail of every `frob ticket accept --amend/--remove`
    # mutation this ticket's `acceptance` has gone through (never edited,
    # only appended) -- makes a weakened-to-force-a-close criterion visible
    # instead of a silent hand-edit of the ledger.
    acceptance_amendments: tuple[AcceptanceAmendmentEntry, ...] = ()
    # frob:ticket T-1733
    # append-only audit trail of every `frob ticket evidence --replace`
    # mutation this ticket's evidence has gone through (never edited,
    # only appended) -- the ScopeChangeEntry/AcceptanceAmendmentEntry
    # discipline applied to evidence: what proves a ticket must be
    # rebindable only with a recorded reason, exactly like what a ticket
    # covers already was.
    evidence_changes: tuple[EvidenceChangeEntry, ...] = ()
    # STRIDE category for kind=security tickets (T-0007)
    threat: Stride | None = None
    # frob:ticket T-0454
    # which module/area this ticket belongs to (gates, strata, dup, vet,
    # deploy, render, tickets, ...) -- freeform, not an enum: the set of
    # components grows with the codebase and a fixed enum would need a
    # migration every time a new subsystem is carved out. `None` means
    # uncategorized, never coerced to an empty string.
    component: str | None = None
    # frob:ticket T-0454
    # freeform tags orthogonal to `component` (cross-cutting concerns like
    # "perf", "security", "flaky") -- `frob ticket board`/`doable` can
    # filter on either axis independently.
    labels: tuple[str, ...] = ()
    # frob:ticket T-1856
    # first-class marker for a ticket that must NEVER reach a terminal
    # state (done/dropped) -- the T-1820/T-1831 "waiver home" shape
    # (docs/modules/gates.md's T-1558 precedent): a `follow_up="T-####"`
    # target for a PERMANENT `frob:waive`, which WIRE002 (unwaivable)
    # disqualifies the moment its target goes terminal. Before this field
    # existed, intent was inferred only from body prose, which nothing
    # enforced -- T-1853's body records the near-miss: an agent was
    # instructed to close T-1820 "to drain the queue" and it was caught
    # only by a different agent noticing, not by the tool. Set via
    # `set_anchor` (`frob.tickets._land`, T-1856); land-time enforcement
    # lives in `_refuse_anchor_terminal_land` in the same module.
    anchor: bool = False
    # frob:ticket T-1856
    # required human-readable justification for `anchor=True`, same
    # "no silent flag flip" discipline `scope_breadth_ack_reason` already
    # established for `scope_breadth_ack` -- `None` when `anchor` is
    # False, set together by `set_anchor`, never independently.
    anchor_reason: str | None = None
    body: str = ""

    @field_validator("scope", mode="before")
    @classmethod
    def _normalize_scope(cls, value: Sequence[str]) -> tuple[str, ...]:
        """Split any comma-joined entry into separate globs on load or
        construction (T-0241) -- see `_split_scope_entries`."""
        return _split_scope_entries(value)

    @field_validator("labels", mode="before")
    @classmethod
    def _normalize_labels(cls, value: Sequence[str]) -> tuple[str, ...]:
        """Split any comma-joined entry into separate labels (T-0454), the
        same normalization `scope` gets from `_split_scope_entries` (T-0241)
        -- a hand-typed `--label 'a,b'` must not become one unmatchable tag."""
        return _split_scope_entries(value)

    @field_validator("acceptance", mode="before")
    @classmethod
    def _coerce_acceptance_field(cls, value: Sequence[object]) -> list[dict | object]:
        """Accept legacy plain-string acceptance items alongside the T-0572
        structured `{text, evidence}` form -- see `_coerce_acceptance`."""
        return _coerce_acceptance(value)

    # T-1132: deliberately NOT validating `blocked_by`/`parent` here (unlike
    # `TicketSpec` below). `Ticket.model_validate` is also the LEDGER LOAD
    # path (`frob.tickets._store._parse_ledger`/`_validate`) -- a strict
    # field validator here would hard-fail loading the ENTIRE shared ledger
    # (all ~1000+ tickets, active+archive) the moment a single historical
    # malformed edge exists anywhere in it, a much worse failure mode than
    # the T-0380 incident itself (one ticket silently miscomputed, not
    # every command refusing to run). New-edge validation lives at the
    # actual write sites instead: `TicketSpec` (used only by `frob ticket
    # new`, never by the loader) and the `_block` CLI verb's explicit
    # `is_valid_ticket_ref` check (`model_copy` bypasses field validators
    # entirely regardless, so putting one here would not even close that
    # gap). `frob doctor`'s malformed-edge scan (T-1132) is the READ-side
    # complement: it flags an EXISTING bad edge without depending on strict
    # `Ticket` construction succeeding.

    # frob:ticket T-0838
    # frob:tests tests/test_tickets.py::TestUnknownFieldForwardCompat.test_unknown_field_logs_warning_named  # noqa: E501
    @model_validator(mode="after")
    def _warn_unknown_extras(self) -> Ticket:
        """Log a WARNING naming every unknown ledger field this ticket
        carried in (T-0838): `extra="allow"` means an unrecognized key no
        longer hard-fails `MalformedFrontmatter`, but it should never be
        silently invisible either -- a human/agent re-reading this ticket
        with an OLDER `frob` needs to know it is looking at a ledger written
        by something newer than itself, and which field(s) it cannot
        interpret."""
        extras = self.__pydantic_extra__
        if extras:
            _log.warning(
                "tickets: %s carries unknown ledger field(s) %s -- likely an "
                "older frob reading a newer ledger; preserved verbatim, not "
                "validated (T-0838)",
                self.id,
                sorted(extras),
            )
        return self

    # frob:ticket T-0838
    # frob:tests tests/test_tickets.py::TestEmptyCollectionOmission.test_reviews_empty_never_serialized  # noqa: E501
    @model_serializer(mode="wrap")
    def _omit_empty_collections_on_dump(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, object]:
        """Wrap the default dump so empty-collection fields (`reviews: []`
        and every peer default-empty tuple field, T-0838) never hit the
        ledger, while unknown extras captured via `extra="allow"` still
        round-trip (pydantic includes `__pydantic_extra__` in the base dump
        this wraps, unaffected by the omission filter below since they are
        rarely empty collections and, even if one were, an unknown field
        omitted on write is exactly as forward-compatible as one that was
        never populated -- it simply reappears once it holds real data)."""
        data = handler(self)
        return _omit_empty_collections(data)


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
    # frob:ticket T-0715
    tier: TicketTier = TicketTier.TICKET
    # frob:ticket T-0715
    sprint: str | None = None
    # frob:ticket T-1613
    # see `Ticket.runs_last` -- settable at filing time via
    # `frob ticket new --runs-last`.
    runs_last: bool = False
    # given/when/then acceptance criteria, each bound to evidence id(s)
    # (T-0572); see `Ticket.acceptance`
    acceptance: tuple[AcceptanceCriterion, ...] = ()
    threat: Stride | None = None
    evidence: tuple[str, ...] = ()
    # frob:ticket T-0454
    component: str | None = None
    labels: tuple[str, ...] = ()
    body: str = ""

    @field_validator("scope", mode="before")
    @classmethod
    def _normalize_scope(cls, value: Sequence[str]) -> tuple[str, ...]:
        """Split any comma-joined entry into separate globs before the spec
        is turned into a `Ticket` (T-0241) -- see `_split_scope_entries`."""
        return _split_scope_entries(value)

    @field_validator("labels", mode="before")
    @classmethod
    def _normalize_labels(cls, value: Sequence[str]) -> tuple[str, ...]:
        """Split any comma-joined entry into separate labels (T-0454) before
        the spec is turned into a `Ticket` -- see `_split_scope_entries`."""
        return _split_scope_entries(value)

    @field_validator("acceptance", mode="before")
    @classmethod
    def _coerce_acceptance_field(cls, value: Sequence[object]) -> list[dict | object]:
        """Accept legacy plain-string acceptance items alongside the T-0572
        structured `{text, evidence}` form -- see `_coerce_acceptance`."""
        return _coerce_acceptance(value)

    # frob:ticket T-1132
    @field_validator("blocked_by")
    @classmethod
    def _validate_blocked_by_field(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Reject an empty-string or malformed `blocked_by` entry at
        `frob ticket new` time (T-1132, the T-0380 incident) -- see
        `_validate_blocked_by`."""
        return _validate_blocked_by(value)

    # frob:ticket T-1132
    @field_validator("parent")
    @classmethod
    def _validate_parent_field(cls, value: str | None) -> str | None:
        """Reject a malformed `parent` entry at `frob ticket new` time
        (T-1132) -- see `_validate_parent`."""
        return _validate_parent(value)


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
# frob:ticket T-0579
# frob:ticket T-0889
# frob:ticket T-1733
# frob:waive AFFECT001 reason="T-1733: TicketError's affects()-closure doc \
# (docs/modules/tickets.md#error-types) genuinely needs the new \
# EvidenceReplaceReasonMissing variant documented -- but docs/modules/tickets.md is \
# leased by another in-progress agent (T-1715/T-1739) for the duration of this \
# ticket's work, so touching it here would collide with that lease. The new variant is \
# documented in this ticket's own docs home instead (docs/modules/gates.md's new \
# 'TEST018 (T-1733)' section); remove this waiver once the tickets.md lease clears and \
# its own error-types entry can be added"
class TicketError(ErrorSet):
    """Fallible outcomes of frob.tickets queue/mutation operations."""

    NotFound = "No ticket with that id"
    DuplicateId = "Ticket id already exists"
    # frob:ticket T-1744
    DuplicateTicket = (
        "an existing ticket already has this exact title and this exact scope"
    )
    MalformedFrontmatter = "Ticket file failed schema validation"
    InvalidTransition = "State change not allowed by the state machine"
    MissingEvidence = "done requires evidence and a Done report"
    MalformedEvidence = "evidence entry failed schema validation"
    BlockerOpen = "Cannot start: blocked_by contains open tickets"
    # frob:ticket T-1613
    RunsLastBlocked = "Cannot start: runs-last ticket while other tickets are open"
    WriteFailed = "Atomic ticket write failed"
    UnknownEvidence = "Evidence id does not resolve to a collected test"
    # T-0215: non-pytest evidence channel for docs-kind tickets
    EvidenceKindNotAllowed = "cmd evidence is only allowed for docs-kind tickets"
    EvidenceCmdFailed = "evidence command failed to launch or exited nonzero"
    # frob:ticket T-1892
    EvidenceCmdSilent = (
        "evidence command exited 0 with empty stdout+stderr -- proves nothing"
    )
    # T-0398 D-01: injected pass/fail oracle says a collected id did not pass
    EvidenceNotPassing = "Evidence id resolved but did not pass when last run"
    # T-0398 D-02: no evidence id binds to a touched/scope symbol
    EvidenceScopeUnbound = "No evidence id covers a touched/scope symbol"
    # T-0455: `frob ticket scope --add/--remove` failure modes
    ScopeChangeEmpty = "scope change requires at least one --add or --remove glob"
    ScopeChangeReasonMissing = "scope change requires a non-empty --reason"
    # frob:ticket T-1484
    ScopeBreadthAckReasonMissing = "scope-ack requires a non-empty --reason"
    # frob:ticket T-1856
    AnchorReasonMissing = "anchor set/clear requires a non-empty --reason"
    ScopeLeaseConflict = (
        "requested --add glob overlaps a path leased by another in-progress ticket"
    )
    ScopeRemoveNotDeclared = "requested --remove glob is not in the ticket's scope"
    # frob:ticket T-1670
    DesignatedReproNotInEvidence = (
        "--designate-repro id is not one of this ticket's bound evidence ids"
    )
    ScopeRemoveOrphansEvidence = (
        "cannot remove a scope glob that already covers recorded evidence"
    )
    # T-0454: `frob ticket label` failure mode -- mirrors ScopeChangeEmpty
    LabelChangeEmpty = "label change requires at least one --add or --remove label"
    # T-0431: FROB_WORKTREE names a leased worktree that does not match the
    # cwd's actual git top-level -- a dispatched agent's shell wandered
    # (accidentally or otherwise) outside its assigned worktree.
    WorktreeLeaseViolation = (
        "FROB_WORKTREE is leased to a different worktree than this command's cwd"
    )
    # T-0579: `frob ticket drop <id> --reason TEXT` failure mode -- a drop
    # with no reason is indistinguishable from a silent discard later.
    DropReasonMissing = "drop requires a non-empty --reason"
    # T-0571: `frob ticket review` failure modes
    ReviewFindingsMissing = "review requires non-empty --findings-file content"
    # T-0571 review round 1: a --commit value (short SHA, ref name, etc.)
    # that does not resolve via `git rev-parse` must never be stored
    # verbatim -- has_approved_review_for_commit does a plain string
    # comparison against a full rev-parse HEAD sha, so an unresolved/
    # unnormalized commit value can never match and would silently make
    # close --strict unsatisfiable forever.
    ReviewCommitUnresolvable = "review --commit does not resolve to a real commit"
    # T-0571: `close --strict` (config-gated) failure mode -- no
    # verdict=approve review record names the current final commit
    MissingApprovedReview = (
        "close --strict requires an approve-verdict review record naming "
        "the current commit"
    )
    # T-0572: `frob ticket evidence --accepts N` / `bind_acceptance` failure
    # modes, and the close-time gate they exist to feed.
    AcceptanceIndexOutOfRange = "--accepts index does not name an acceptance item"
    AcceptanceUnbound = "one or more acceptance criteria have no resolving evidence id"
    # T-1029: `frob ticket accept <id> --criterion TEXT` (append acceptance
    # criteria to an EXISTING ticket) failure mode -- mirrors
    # ScopeChangeEmpty/LabelChangeEmpty's "don't call this for nothing"
    # discipline.
    AcceptanceChangeEmpty = "accept requires at least one non-blank --criterion"
    # T-1422: `frob ticket accept --amend/--remove` failure modes -- mirrors
    # ScopeChangeReasonMissing/ScopeRemoveNotDeclared's "don't call this
    # for nothing, and be accountable" discipline.
    AcceptanceAmendIndexOutOfRange = (
        "--amend/--remove index does not name an acceptance item"
    )
    AcceptanceAmendReasonMissing = "amend/remove requires a non-empty --reason"
    AcceptanceAmendTextMissing = "--amend requires non-empty replacement --text"
    AcceptanceAmendTerminalState = (
        "cannot amend acceptance on a ticket already in a terminal (done/dropped) state"
    )
    # T-0844: `close` (not just `land`) refuses a security/bug-kind ticket
    # whose bound evidence killed zero mutants (TEST016 at ERROR severity),
    # mirroring LandError.EvidenceConfirmatoryOnly -- see
    # `frob.tickets._done_transition_guard`'s `mutation_evidence` parameter.
    EvidenceConfirmatoryOnly = (
        "confirmatory-only evidence (TEST016 ERROR) for a security/bug-kind "
        "ticket; strengthen the named evidence tests or retry close with "
        "--skip-mutation-evidence"
    )
    # T-0854: the T-0605-orphaned-41-rows incident class -- a ticket cannot
    # close/land while a registry disposition (`deferred:<id>`) or a
    # `frob:waive`/`.strata waive` `ticket=` attribute still cites it as
    # its live tracker; see `frob.tickets._live_tracker.live_tracker_citations`.
    LiveTrackerCited = (
        "registry dispositions or waivers still cite this ticket as their "
        "live tracker; file a successor and re-point the citing rows, or "
        "re-point them in this same change, then retry"
    )
    # T-0764: `archive()` refuses (unless `force=True`) when a ticket it
    # would move into tickets-archive.md still holds a live cross-worktree
    # lease -- archiving during in-flight work is the hazard the T-0753
    # incident traced to. T-0843: the CLI surface is `--force`, not the
    # internal `force=True` kwarg -- the hint must name a copy-pastable
    # command, per the repo's own violation-message convention.
    ArchiveLiveLeaseExists = (
        "a ticket this call would archive has a live in-flight lease; "
        "archiving now would run concurrently with in-flight work -- run "
        "in a quiet window or pass --force to override"
    )
    # T-0764: a ledger write whose rendered text would produce a section
    # with no marker line, or silently drop an id its input carried, is
    # refused rather than committed -- the structural guard for the
    # T-0367 markerless-block/id-drop incident class.
    LedgerIntegrityViolation = (
        "rendered ledger text lost a ticket id or marker -- write refused"
    )
    # frob:ticket T-1721
    # `_splice_only_ticket` (T-0479) scopes a land's own ledger overlay to
    # ONLY the ticket being landed -- every sibling id comes from main
    # untouched by default, which is correct when the worktree's sibling
    # copy is merely STALE, but silently drops a genuine edit the worktree
    # made to a sibling's own section (e.g. `frob ticket evidence <other>
    # --replace ...`) whenever main ALSO changed that same sibling section
    # since the worktree's fork point, in a way that does not converge to
    # the same content. Neither side is "wrong" here -- both made a real,
    # independent edit -- so silently picking one (the old T-0682/T-0764
    # richness heuristic, or T-0479's blanket main-wins default) would
    # discard real work no matter which side it picked. Refused instead,
    # naming the conflicting id, so an operator resolves it explicitly
    # rather than the land silently choosing a winner.
    SiblingLedgerEditConflict = (
        "a sibling ticket's ledger section was independently edited on "
        "both main and the worktree since their common base, in ways that "
        "do not converge -- refusing rather than silently picking a side"
    )
    # T-1179: a land-time ticket-scoped splice (`_splice_only_ticket`) whose
    # overlay id already exists on main's side under a DIFFERENT title is a
    # collision between two unrelated tickets sharing one id, not a genuine
    # same-ticket divergence `_newer` should silently arbitrate -- refuse
    # loudly instead of overwriting either side (defense in depth alongside
    # the T-1179 main-fresh id-ceiling fix; see `_splice_only_ticket`).
    IdTitleMismatch = (
        "landing block's id already exists on main under a different title "
        "-- refusing to overwrite"
    )
    # frob:ticket T-1637
    # A write that would replace an existing ticket id's content with a
    # version carrying NO evidence and NO "## Done report" section, when
    # the on-disk version being overwritten had one or the other -- the
    # one-level-down sibling of LedgerIntegrityViolation (T-0764/T-1536
    # protects against a ticket id vanishing entirely; this protects
    # against the id surviving but its already-done WORK vanishing). The
    # T-1636 field incident this exists to prevent: a hand-rolled draft
    # refile recipe (`frob ticket new` on main, then delete the draft's
    # own block) discarded 12 evidence ids and a 12KB Done report with no
    # warning at all, recoverable only via `git show <sha>~1:tickets.md`
    # archaeology.
    DoneReportOrEvidenceDiscarded = (
        "this write would replace an existing ticket's evidence/Done "
        "report with an empty one -- refusing (T-1679: this is now "
        "write_ticket()'s DEFAULT; strict_no_content_loss=False is the "
        "explicit opt-out that logs the same finding as a warning "
        "instead of refusing)"
    )
    # T-0889: a wholesale `write_all`/`write_archive` caller that captured
    # a digest of the ledger at load time and passed it back as
    # `expected_digest` gets THIS instead of a silent clobber when the
    # on-disk ledger no longer matches that digest -- some other writer
    # (or an external `git checkout`/restore) changed it since the load,
    # and the caller's in-memory map is a stale snapshot that would
    # otherwise overwrite whatever changed. The T-0680 field incident
    # this closes: three unrelated done tickets (T-0660/T-0661/T-0719)
    # were silently reverted to queued with evidence/Done reports wiped
    # by exactly this class of blind wholesale write.
    LedgerChangedSinceLoad = (
        "ledger changed on disk since this caller's load -- reload and "
        "retry rather than overwriting with a stale snapshot"
    )
    # T-0756: a ticket whose diff adds a new gate rule id (a fresh
    # `_KNOWN_GATE_RULES` entry, `frob.gates`'s own rule registry) but
    # carries no bound acceptance criterion proving a fixture failed
    # before and passed after through the production invocation -- see
    # `frob.tickets._new_gate_rule_acceptance`.
    NewGateRuleUnaccepted = (
        "diff adds a new gate rule id with no bound before-fails/after-passes "
        "fixture acceptance criterion; record one proving the rule fires "
        "through the production invocation, then retry"
    )
    # T-1937/T-1956: a ticket whose OWN declared scope constructs a rule id
    # (`rule=`/`code=`/a typed const assignment/a bare positional arg,
    # `frob.gates._rule_id_scan.find_unregistered_rule_ids`'s broad,
    # shape-agnostic net) that is missing from `_KNOWN_GATE_RULES`
    # entirely -- distinct from NewGateRuleUnaccepted above, which only
    # fires once an id is ALREADY in the registry; this fires BEFORE that,
    # closing the soundness hole T-1937's audit found where a constructed-
    # but-never-registered rule id bypasses the T-0756 preflight
    # completely (there is no registry-side diff to detect). See
    # `frob.tickets._new_gate_rule_acceptance.unregistered_rule_ids_in_scope`.
    UnregisteredGateRuleConstructed = (
        "diff constructs gate rule id(s) not yet registered in "
        "_KNOWN_GATE_RULES at all; add the entry (frob.gates._waive) before "
        "this ticket can close -- an unregistered id cannot carry T-0756 "
        "acceptance evidence either, since the acceptance preflight only "
        "ever sees ids already in the registry"
    )
    # T-0887: `frob ticket done-report --base-ref <ref>` used to spend
    # minutes discovering a typo'd/unfetched base ref indirectly (a `git
    # diff --stat` that silently returned no lines, or a downstream `frob
    # check --ticket` spawn) instead of failing on the ref itself, in
    # seconds, up front. See `frob.tickets._base_ref_resolution`.
    BaseRefUnresolvable = (
        "base ref does not resolve to a commit in this clone; fetch it or "
        "pass a base ref that exists, then retry"
    )
    # T-0715: an EPIC/STORY tier ticket refuses `done` while any descendant
    # (via the `parent` chain, any depth) is still open -- see
    # `frob.tickets._open_descendant_ids`.
    OpenDescendant = (
        "an epic/story ticket cannot close while a descendant ticket is "
        "still open; close or drop the descendant(s) first"
    )
    # T-1384: `close` refuses (when the caller injects
    # `own_obligations_clean=False`) while the ticket's OWN diff leaves a
    # new public symbol with no `frob:doc` edge, a new public test class
    # undeclared on its testsuite strata node, or a changed public API with
    # no REL001 bump -- the T-1377/T-1379/T-1381 residue class (closed
    # clean, then the very next unscoped `frob check` showed the closer's
    # own COV001/SELFAUDIT/REL findings as a surprise). See
    # `frob.tickets._done_transition_guard`'s `own_obligations_clean`
    # parameter.
    OwnObligationsUnclean = (
        "this ticket's own diff leaves a new-symbol doc edge, testsuite "
        "declaration, or REL001 bump outstanding; run `frob check --delta` "
        "(or the named gate) and resolve the finding(s) it names, then retry"
    )
    # T-1399: a criterion asserting a package-wide gate outcome ("0 <RULE>
    # findings under <glob>") is only satisfied by evidence that actually
    # ESTABLISHES that outcome -- binding an unrelated passing node id makes
    # `unbound_acceptance` formally satisfied while the underlying claim
    # stays false (the T-1276 incident: closed done, LAND-PROOF verified,
    # 116 live TEST005 findings under the exact glob the criterion named).
    # Refuses (when the caller injects `gate_claims_verified=False`) while
    # ANY of the ticket's acceptance criteria reads in this shape -- see
    # `frob.tickets._evidence._gate_claim_criteria`/`_criterion_gate_claim`.
    GateClaimUnverified = (
        "an acceptance criterion asserts a package-wide gate outcome (0 "
        "<RULE> findings under <glob>) that the bound evidence does not "
        "establish; run the named gate against the named glob and record "
        "its result, then retry"
    )
    # frob:ticket T-1537
    #: `frob ticket evidence <id> --replace <old-node> <new-node>` failure
    #: mode: `old-node` names nothing this ticket's evidence list OR any
    #: acceptance criterion's evidence tuple actually holds -- a typo'd
    #: `--replace` source id must never silently no-op.
    EvidenceReplaceNotFound = (
        "--replace old-node is not present in this ticket's evidence list "
        "or any acceptance criterion's evidence"
    )
    # frob:ticket T-1733
    #: `frob ticket evidence <id> --replace <old-node> <new-node>` with no
    #: `--reason`/`--reason-file` -- the T-0455 `frob ticket scope`
    #: precedent applied to evidence: rebinding/weakening what proves a
    #: ticket must be a recorded decision, exactly like narrowing what it
    #: covers already is. Pure `add_evidence` appends stay unaffected --
    #: only the shrink/rebind path costs this.
    EvidenceReplaceReasonMissing = (
        "--replace requires a non-empty --reason or --reason-file (T-1733)"
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
    # frob:ticket T-1920
    BranchDrift = (
        "root's checked-out branch drifted away from the branch this land "
        "began operating on, discovered immediately before the final "
        "squash commit -- refused by construction so no terminal ticket "
        "state or REL001 bump is ever committed onto a branch other than "
        "the one 'main' names (the T-1895 incident shape)"
    )
    ClaimDivergence = (
        "captured Done-report claims (test count or gate state) no longer "
        "hold post-merge (T-0754)"
    )
    # frob:ticket T-0755
    EvidenceConfirmatoryOnly = (
        "a security/bug-kind ticket's bound evidence killed zero mutants of "
        "its own diff-touched code -- confirmatory-only, TEST016"
    )
    # T-0854: the T-0605-orphaned-41-rows incident class -- see
    # TicketError.LiveTrackerCited (same remedy, land-time twin).
    LiveTrackerCited = (
        "registry dispositions or waivers still cite this ticket as their live tracker"
    )
    # T-0631: mirrors gates.TICK005's regression semantics, run directly
    # around this land's own squash-splice (a squash-apply never produces
    # the two-parent merge commit TICK005-the-gate requires to fire).
    TerminalStateRegression = (
        "a terminal (DONE/DROPPED) ticket would regress to a non-terminal "
        "state via this land's ledger splice (TICK005 regression sweep)"
    )
    # T-1323: the 2026-07-29 incident's own laundering path -- an
    # uncommitted `frob:waive` DELETION in the worktree, wip-snapshotted
    # and squash-applied onto main, whose file is neither in the landing
    # ticket's scope nor declared by its Done report.
    OutOfScopeWaiveDeletion = (
        "worktree has an uncommitted frob:waive deletion outside the "
        "landing ticket's scope and Done report"
    )
    # frob:ticket T-1355
    CrossTicketLeakage = (
        "the branch's committed changeset touches file(s) covered by a "
        "DIFFERENT ticket's declared scope, and that ticket is still open "
        "(not done/dropped) on main -- landing would silently carry a "
        "sibling ticket's work onto main ahead of its own close"
    )
    # frob:ticket T-1269
    PlanTickGateDirty = (
        "frob ticket land --plan's post-merge TICK gate re-check reported "
        "a non-clean result -- the merge and any draft finalization were "
        "fully unwound"
    )
    # frob:ticket T-1515
    LandLockTimeout = (
        "root's land.lock is still held by another process/session after "
        "the T-1515 wait timeout -- a foreign or orphaned land driver may "
        "be mid-run; inspect `frob doctor`'s live-land-process report "
        "before retrying"
    )
    # frob:ticket T-1514
    PreLandUnscopedSweepFailed = (
        "the unscoped error sweep against the staged, pre-commit merge "
        "preview found new error(s) no Tier-A auto-fix could resolve -- "
        "the staged squash was unwound before any commit landed on main "
        "(T-1514: refusing here, before the commit exists, is what makes "
        "this refusal free -- see the post-land sweep, T-1456, for the "
        "cheap post-commit assertion this complements)"
    )
    # frob:ticket T-1444
    PostLandUnscopedSweepFailed = (
        "the post-land unscoped error sweep (T-1456) found residue no "
        "Tier-A auto-fix could resolve -- the commit already landed on "
        "main and was reverted via `git reset --hard` back to its "
        "pre-land state; a single interactive `frob ticket land` call "
        "reports this via sys.exit(1) directly (see the post-land sweep "
        "sequence in _land_cmd.py), this member exists so a drain "
        "loop (T-1444) processing several queued lands in one process "
        "can attribute the failure to its own ticket and continue "
        "draining the rest instead of the whole loop dying with it"
    )
    # frob:ticket T-1618
    PassengerTickets = (
        "the branch's diff carries frob:ticket directive additions naming "
        "ONE OR MORE OTHER ticket ids -- landing this worktree branch "
        "would carry that other ticket's committed code onto main as an "
        "undisclosed passenger of this ticket's own land (T-1618); pass "
        "--allow-cross-ticket to acknowledge and proceed deliberately"
    )
    # frob:ticket T-1618
    AlreadyLandedOnMain = (
        "the ticket's own declared scope has no changes on this branch "
        "relative to main -- its content is very likely ALREADY on main "
        "(T-1618, the common consequence of a passenger-ticket land: "
        "another ticket's land already carried this one's own code); "
        "verify by hand and close directly instead of retrying this land"
    )
    # frob:ticket T-1721
    # Land-level twin of TicketError.SiblingLedgerEditConflict -- surfaced
    # distinctly from the generic GitFailed so an operator sees "a sibling
    # ticket's section conflicts, resolve by hand" rather than an opaque
    # git-operation failure.
    SiblingLedgerEditConflict = (
        "a sibling ticket's ledger section was independently edited on "
        "both main and the worktree since their common base, in ways that "
        "do not converge -- resolve the conflicting sibling ticket's "
        "section by hand (or land it on its own first), then retry"
    )
    # frob:ticket T-1856
    AnchorTerminalLand = (
        "this ticket is marked anchor=True (a permanent frob:waive "
        "follow_up target that must never go terminal, T-1856) and this "
        "land would move it to done/dropped -- clear the marker first "
        "(frob.tickets._land.set_anchor(root, id, anchor=False, "
        "reason=...)) if it genuinely no longer needs to anchor a "
        "waiver, or land it as queued/in-progress/blocked instead"
    )


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


# frob:ticket T-1269
# frob:doc docs/modules/tickets.md#frob-ticket-land---plan-t-1269
class LandPlanReport(BaseModel):
    """Outcome of one `land_plan()` call (`frob ticket land --plan`): a
    design-phase worktree (docs + ledger changes, no closeable worked
    ticket) merged onto `root` and every incoming draft id it carried
    finalized to a real `T-####` id, all in one atomic commit."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dry_run: bool
    merge_commit: str | None = None
    finalized: tuple[tuple[str, str], ...] = ()
    commit_sha: str | None = None


# frob:ticket T-0454
# frob:doc docs/modules/tickets.md#public-api
# The fixed column order `frob ticket board` renders in -- left-to-right the
# same direction work actually flows, so a glance at the board reads like a
# pipeline rather than an arbitrary bucket dump. DROPPED is last (dead work,
# not a destination).
BOARD_STATES: tuple[TicketState, ...] = (
    TicketState.QUEUED,
    TicketState.PLANNED,
    TicketState.IN_PROGRESS,
    TicketState.BLOCKED,
    TicketState.DONE,
    TicketState.DROPPED,
)


# frob:ticket T-0454
# frob:doc docs/modules/tickets.md#public-api
class BoardColumn(BaseModel):
    """One state-column of `frob ticket board`: its tickets, priority-then-age
    ordered (the same key `doable` uses, T-0411)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    state: TicketState
    tickets: tuple[Ticket, ...] = ()


# frob:ticket T-0454
# frob:doc docs/modules/tickets.md#public-api
class EpicRollup(BaseModel):
    """`frob ticket epic <id>`'s subtree summary: every descendant (via the
    `parent` chain, any depth), how many are DONE vs the total, and which
    LEAF descendants (no children of their own) are currently BLOCKED --
    the two numbers a human scanning an epic actually wants first."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    epic: Ticket
    descendants: tuple[Ticket, ...] = ()
    done: int = 0
    total: int = 0
    blocked_leaves: tuple[str, ...] = ()

    @property
    # frob:doc docs/modules/tickets.md#public-api
    def percent_complete(self) -> float:
        """`done / total * 100`, or `0.0` for a childless epic (never
        divides by zero)."""
        if self.total == 0:
            return 0.0
        return (self.done / self.total) * 100.0


# frob:ticket T-0715
# frob:doc docs/modules/tickets.md#data-models
class SprintReport(BaseModel):
    """`frob ticket sprint show <label>`'s commitment summary (T-0715):
    every ticket carrying this `sprint` label, a `TicketState -> count`
    rollup, and `closed` (the done-count velocity number) -- derived
    entirely from the tickets' current `state`, no separate tracked
    counter."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sprint: str
    tickets: tuple[Ticket, ...] = ()
    rollup: Mapping[TicketState, int] = {}
    closed: int = 0


# frob:ticket T-0938
# frob:doc docs/modules/tickets.md#data-models
class SprintTransition(BaseModel):
    """One mined `state: done` transition (T-0938) for a single ticket,
    read from `tickets.md`'s own git history: `sprint_velocity` walks
    every commit that ever touched the ledger and reads this ticket's
    `state:` value out of that commit's blob -- the "no new storage"
    derivation source: no field on this model is ever hand-set or
    persisted outside git's own commit log."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticket_id: str
    sha: str
    committed_at: datetime
    from_state: str | None
    to_state: str


# frob:ticket T-0938
# frob:doc docs/modules/tickets.md#data-models
class SprintVelocityReport(BaseModel):
    """`frob ticket sprint velocity <label>`'s history-derived summary
    (T-0938): every mined `SprintTransition` into `done` for tickets
    currently committed to this sprint, ordered oldest-first (a burndown
    timeline), plus `closed`/`remaining`/`total` counts. Unlike
    `SprintReport.closed` (a snapshot of CURRENT ledger state),
    `transitions` is mined from `tickets.md`'s git history -- see
    `frob.tickets.sprint_velocity`'s docstring for exactly what that can
    and cannot see."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sprint: str
    transitions: tuple[SprintTransition, ...] = ()
    closed: int = 0
    remaining: int = 0
    total: int = 0


# frob:ticket T-1100
# frob:doc docs/modules/tickets.md#public-api
class TicketFlowRow(BaseModel):
    """One calendar day's `frob ticket flow` counts (T-1100): tickets FILED
    that day (`Ticket.created` matching, the same field `sprint_view`/
    `board_view` already read, no new storage), tickets LANDED that day
    (mined the same way `sprint_velocity`'s `SprintTransition` is, via
    `_mine_done_transitions` over the WHOLE queue rather than one sprint),
    and `net = filed - landed` -- positive means the queue is growing that
    day, negative means it is shrinking."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    day: date
    filed: int = 0
    landed: int = 0

    @property
    # frob:ticket T-1100
    # frob:doc docs/modules/tickets.md#public-api
    # frob:tests tests/test_tickets_velocity.py::TestTicketFlow.test_filed_and_landed_counted_per_day kind="unit"  # noqa: E501
    def net(self) -> int:
        """`filed - landed` for this day; positive grows the queue,
        negative shrinks it."""
        return self.filed - self.landed


# frob:ticket T-1528
# frob:ticket T-1100
# frob:doc docs/modules/tickets.md#public-api
class TicketFlowReport(BaseModel):
    """`frob ticket flow`'s full report (T-1100): one `TicketFlowRow` per
    calendar day from the earliest observed filing/landing event through
    today (zero-filled, never sparse -- a day with no activity still gets
    a row so `trailing_net_rate` always averages a real fixed-size window),
    the CURRENT open-ticket count (a live snapshot, not mined history), the
    trailing-3-day average net rate, and a naive burn-down ETA in days
    (`open_count / trailing_net_rate` when the rate is actually shrinking
    the queue; `None` when it is flat or growing, since dividing by a
    non-positive rate would either raise or produce a nonsensical negative
    ETA -- `frob ticket flow`'s render layer is expected to label a `None`
    ETA as "cannot estimate: not shrinking", never silently omit the
    line)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rows: tuple[TicketFlowRow, ...] = ()
    open_count: int = 0
    trailing_net_rate: float = 0.0
    # frob:ticket T-1528
    #: Median calendar days from `created` to first observed done
    #: transition across every ticket that has both; None when no ticket
    #: has completed yet (render layers label it "n/a", never omit).
    median_cycle_days: float | None = None

    @property
    # frob:ticket T-1100
    # frob:doc docs/modules/tickets.md#public-api
    # frob:tests tests/test_tickets_velocity.py::TestTicketFlow.test_eta_none_when_queue_not_shrinking kind="unit"  # noqa: E501
    # frob:tests tests/test_tickets_velocity.py::TestTicketFlow.test_eta_computed_when_queue_shrinking kind="unit"  # noqa: E501
    def eta_days(self) -> float | None:
        """`open_count / trailing_net_rate` (a naive, disclosed
        extrapolation, not a forecast) when the trailing rate is actually
        NEGATIVE (the queue is net-shrinking) -- `None` when the queue is
        flat or growing, since burn-down has no meaningful ETA in that
        case."""
        if self.trailing_net_rate >= 0:
            return None
        return self.open_count / -self.trailing_net_rate
