# frob:waive LARGE001 reason="T-2851-grade: this file IS the extracted single \
# repro-classification concern its own module doc names -- one worktree checkout / \
# subprocess spawn / exit-classify pipeline (_checkout_bug_repro_worktree -> \
# _spawn_designated_test -> _classify_designated_test_exit -> _run_designated_test, \
# threaded through the shared _bug_repro_outcome_at_ref classifier) with exactly two \
# consumers layered on top (bug_repro_violations for BUG002, \
# must_still_pass_violations for BUG003) that both call the SAME classifier rather \
# than duplicating it, plus their message builders and the frob:waive \
# BUG002/frob:no-behavior-change/frob:must-still- pass ticket-body directive parsers \
# those two consumers need. Splitting further would separate the \
# checkout/spawn/classify pipeline from the one classifier that calls it in sequence, \
# or separate BUG002 from BUG003 despite them sharing that same classifier -- both \
# cuts sever a real call chain rather than find an independent consumer set, the same \
# T-1651 bar this repo already applies to its other cohesive guard-chain/pipeline \
# modules (frob.tickets._land_squash, frob.tickets._land_release). This module's own \
# doc explains why it is load-bearing enough to deserve a dedicated review pass \
# instead of a further forced cut: bug_repro_outcome_at_ref is frob.tickets._land's \
# pre-land check and frob.app.ticket_runner's close-time CLI path, both called \
# directly."

"""BUG002/must-still-pass repro-classification family (T-2851, split out
of frob.gates._mutation_evidence -- that module's own frob:waive LARGE001
documents this as its filed follow-up).

Parent-commit repro classification for bug/security-kind tickets:
`bug_repro_outcome_at_ref` (public entrypoint, T-1929) is the SINGLE place
that spawns and classifies a repro subprocess against a parent ref --
`frob.app.ticket_runner._verify`'s `--designate-repro`/`--check-repro`
paths and `bug_repro_violations` (the land/close-time BUG002 consumer,
called from `frob.tickets._land` and `frob.app.ticket_runner._close_cmd`)
both go through it, so there remains exactly one place that does this
work. `must_still_pass_violations` (BUG003, T-2215) reuses the same
`_bug_repro_outcome_at_ref` classifier for a ticket's OWN designated
control test, wired from `frob.tickets._land`.

`frob.gates._mutation_evidence` re-exports this module's public names
(`BugReproOutcome`, `bug_repro_outcome_at_ref`, `bug_repro_violations`,
`designated_repro_test`, `must_still_pass_violations`) so `frob.gates.
__init__`'s existing `from frob.gates._mutation_evidence import (...)`
needed no change for this split -- see T-2851's Done report."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from enum import Enum, auto
from pathlib import Path

from typani import Err, Ok, Result

from frob.gates._models import Severity, Violation
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.process._guard import ProcessGuardError, exec_enabled, guarded_subprocess_run
from frob.tickets._models import Ticket

_log = get_logger(__name__)


#: BUG002's own subprocess budget for running ONE designated evidence test
#: at the ticket's parent commit -- generous enough for a small evidence
#: suite, bounded so a hang cannot stall a land indefinitely (mirrors
#: `_TIMEOUT_S` above, T-0755's own per-mutant budget, at 2x since this
#: check runs the whole evidence test once rather than a single mutant).
_BUG_REPRO_TIMEOUT_S = 60.0

#: `git worktree add`/`remove` get their own, smaller budget -- a plain
#: checkout of an existing commit, no build step involved.
_BUG_REPRO_WORKTREE_TIMEOUT_S = 30.0

#: `frob:waive BUG002 reason="..." ` -- BUG002's escape hatch (T-1421,
#: modeled on `--skip-mutation-evidence`'s loud/justification-required
#: posture). Deliberately a plain regex scan of the TICKET'S OWN BODY TEXT
#: rather than a `frob.graph` `WAIVE` edge: `frob.graph.build_graph`
#: excludes `tickets.md` from both its doc-file and source-file walks
#: (see `frob.graph._collect_files`'s `is_ledger` exclusion) precisely so
#: a Done report quoting `frob:waive`/`frob:describes` verbatim does not
#: resurrect a phantom edge -- so a waiver comment physically placed in
#: `tickets.md` can never become a real `WAIVE` edge for
#: `_waive.py`'s`_match_waiver`/`_apply_waivers` spine to find. Scanning
#: `ticket.body` directly (the one place a bug ticket's own justification
#: naturally lives) is therefore not a shortcut around that machinery --
#: it is the only place this override CAN live for a ledger-resident
#: ticket. Requires `reason="..."` to actually suppress (same as
#: WAIVE001's contract elsewhere in this repo); a bare `frob:waive BUG002`
#: with no parseable reason is treated as ABSENT (the check still runs)
#: rather than a silent pass.
#:
#: T-2870: escape-aware value grammar (`\"` does NOT terminate the
#: value), the exact same fix T-2857 applied to `frob.graph.dsl`'s
#: markdown `frob:waive` regex (`_MD_WAIVE_VALUE_RE`) -- this is a SECOND,
#: independent implementation of the same "waive with reason=" shape,
#: living here rather than routed through `frob.graph.dsl` because (per
#: the module docstring above) `tickets.md`/`ticket.body` is deliberately
#: excluded from the general markdown graph walk, so there is no shared
#: call path to reuse without also breaking that exclusion. Kept as an
#: explicit, documented duplication rather than a silent one: if this
#: value grammar ever needs a third fix, check `_MD_WAIVE_VALUE_RE` too,
#: and vice versa -- the two are meant to accept exactly the same shape.
_BUG002_WAIVER_RE = re.compile(
    r'frob:waive\s+BUG002\s+reason="(?P<value>(?:[^"\\]|\\.)*)"'
)

#: T-2870: a looser "shape-like" match -- `frob:waive BUG002 reason=`
#: (an attempt at the reason attribute specifically), WITHOUT requiring
#: the value to actually be well-formed. Used only to detect the
#: silent-drop incident this ticket exists to fix (T-2857 mode 2,
#: measured): an agent writes `frob:waive BUG002 reason=` with a bare,
#: UNQUOTED value (no opening `"` at all), or opens `reason="` but never
#: closes it anywhere in the rest of the body -- both shapes make
#: `_BUG002_WAIVER_RE` above simply not match, which `_bug002_waiver_
#: reason` used to treat exactly like "no waiver was ever attempted"
#: (BUG002 runs silently, no diagnostic). `_bug002_malformed_waiver`
#: below distinguishes those two outcomes: a candidate match here with
#: no corresponding `_BUG002_WAIVER_RE` match at the SAME start position
#: means a waiver was ATTEMPTED and could not be parsed, which must be
#: reported loudly instead of silently falling through.
#:
#: Deliberately requires `reason=` to already be present (not just bare
#: `frob:waive BUG002`) -- a measured false positive during this fix's
#: own repo-wide scan: `tickets/T-1748/ticket.md` discusses the mechanism
#: in plain prose ("...plus a frob:waive BUG002 on the second -- both
#: checks disabled...") with no `reason=` anywhere nearby and no quoting
#: markup at all, so `_is_quoted`'s code-span/blockquote exclusion (T-2218)
#: does not apply to it either. A bare `frob:waive BUG002` mention with no
#: `reason=` attempt is exactly as likely to be prose ABOUT the mechanism
#: as a genuine (if incomplete) attempt to invoke it, so it is left as
#: "silently absent" (unchanged, pre-existing behavior) rather than risk
#: a false "malformed" warning against real ticket prose; only once
#: `reason=` itself appears is intent to waive rather than mere mention.
#:
#: Deliberately does NOT attempt to also catch a genuinely UNESCAPED
#: internal `"` splitting an otherwise-quoted value mid-sentence (T-2857
#: mode 1's shape) -- unlike a markdown anchor's single physical line
#: bounded by a `-->` terminator, a ticket body's `reason="..."` value is
#: free-form prose that legitimately spans multiple lines and
#: parenthetical asides (this repo's own tickets/ already carry several
#: multi-paragraph BUG002 waivers), so there is no safe, terminator-
#: bounded "end of directive" to tail-check the way `frob.graph.dsl._md_
#: waive_reason_tail_error` does for one markdown line without risking a
#: false positive against those live waivers. If a genuine instance of
#: that specific shape is ever measured for BUG002 (as opposed to
#: markdown), it should reuse `_MD_WAIVE_VALUE_RE`'s escape-aware grammar
#: rather than re-deriving a bespoke tail-check here.
_BUG002_WAIVER_CANDIDATE_RE = re.compile(r"frob:waive\s+BUG002\s+reason=")

#: `frob:no-behavior-change reason="..."` (T-1616): the honest home for
#: refactor/deletion-shaped work filed as `bug`/`security` kind (there is
#: no `refactor` kind -- T-1616's own text weighed adding one against a
#: body-text attribute and picked the attribute, mirroring
#: `_BUG002_WAIVER_RE`'s precedent immediately above rather than adding a
#: new `Ticket` field + CLI verb for a single gate's own obligation-swap).
#: When present, BUG002's whole check INVERTS (see `bug_repro_violations`)
#: instead of being skipped: the designated evidence test must PASS at the
#: parent commit (proving behavior is unchanged there too), and a genuine
#: FAILURE at the parent becomes the violation -- the work's own claim
#: ("nothing behavioral changed") would be falsified by its own repro
#: test failing at the pre-change commit. This keeps a real, mechanically
#: checked obligation rather than removing one, per T-1616's requirement
#: that reclassification-shaped work get a swapped obligation, not a
#: skipped one. Same `reason="..."` requirement as `_BUG002_WAIVER_RE`; a
#: bare directive with no parseable reason is treated as ABSENT (the
#: ordinary defect-repro check still runs).
_NO_BEHAVIOR_CHANGE_RE = re.compile(r'frob:no-behavior-change\s+reason="([^"]*)"')

#: `frob:must-still-pass NODE-ID` (T-2193): the explicit, author-named
#: positive-direction control BUG002 has no counterpart for. BUG002/
#: TEST016 both only ever prove a NEGATIVE claim -- a repro test that
#: failed before this ticket's change, or a mutant this ticket's evidence
#: kills -- so a fix that NARROWS a decision rule (resolution, matching,
#: filtering, gating) until it silently accepts/matches NOTHING passes
#: both checks vacuously: there is no surviving false positive to find
#: (BUG002/TEST016 are satisfied), and there is also no proof the
#: narrowed rule still accepts anything real (T-2156/T-2177/`frob cycle`
#: -- see this module's own docstring reference and T-2193's ticket body
#: for the three measured instances, all of which passed every existing
#: gate). `_must_still_pass_controls` below extracts each declared
#: NODE-ID from `ticket.body` verbatim (same body-text-scan rationale as
#: `_BUG002_WAIVER_RE`/`_NO_BEHAVIOR_CHANGE_RE` immediately above -- there
#: is no `Ticket` model field for this, deliberately: this ticket's own
#: scope is this file alone, and the body-text directive is the only
#: mechanism reachable without touching `frob.tickets._models`/the CLI
#: parsers). A bare `frob:must-still-pass` with no NODE-ID is ignored
#: (matches nothing), same as a bare `frob:waive` with no `reason=`.
_MUST_STILL_PASS_RE = re.compile(r"frob:must-still-pass\s+(\S+)")




class _BugReproOutcome(Enum):
    """The six possible outcomes of running BUG002's single designated
    reproduction test against the ticket's parent commit."""

    #: The test genuinely FAILED at the parent commit (pytest exit 1) --
    #: the honest, expected signal that the defect reproduced there and
    #: this ticket's evidence distinguishes parent from fix. No violation.
    FAILED_AT_PARENT = auto()
    #: The test PASSED at the parent commit (pytest exit 0) -- the
    #: evidence does not prove anything changed; this is the T-1384-class
    #: gap BUG002 exists to catch.
    PASSED_AT_PARENT = auto()
    #: The exec kill switch (`FROB_DISABLE_EXEC`) is active, or the
    #: worktree checkout / subprocess spawn itself failed for
    #: infrastructure reasons (not a test result at all -- a collection
    #: error from a missing native extension at the parent commit is the
    #: expected shape here, since a fresh `git worktree add` checkout has
    #: no compiled `frob_core`/`strata_core` of its own). Degrades to "no
    #: verdict", never a false-clean pass and never a false violation --
    #: same posture `MutationEvidenceError.ExecDisabled` already uses one
    #: function up in this same module.
    NO_VERDICT = auto()
    #: The designated test spawn HIT ITS TIME BUDGET (T-2480) -- the
    #: subprocess was still running when `timeout_s` elapsed and was
    #: killed, never allowed to reach a real exit code at all. Distinct
    #: from `NO_VERDICT`'s other infra-failure causes (spawn refused,
    #: kill switch, collection error) because it carries DIFFERENT
    #: information for a reader: "this test may well genuinely
    #: reproduce the defect, but could not be MEASURED within the
    #: budget" is not the same fact as "something about the environment
    #: or the test itself made a verdict impossible". T-2480's own
    #: motivating incident: a repro test that elaborates the full strata
    #: design plus the entire SYS gate legitimately exceeds a 60s budget
    #: on real hardware, and repro tests for architecture/design-level
    #: defects are STRUCTURALLY the slowest ones (demonstrating the
    #: defect means elaborating the whole model) -- so a fixed budget
    #: selectively disenfranchises exactly the repro tests covering the
    #: broadest, highest-consequence defects. Every caller that already
    #: treats `NO_VERDICT` as "cannot be trusted as evidence" must treat
    #: `TIMEOUT` identically for that same purpose (never a false
    #: `FAILED_AT_PARENT`/`PASSED_AT_PARENT`) -- the split exists so the
    #: MESSAGE a human or `--designate-repro-force`'s recorded reason
    #: sees can say "budget exceeded, raise --repro-timeout-s or
    #: re-measure" instead of the generic NO_VERDICT wording, not so any
    #: caller's gating logic branches on it specially.
    TIMEOUT = auto()
    #: `base_ref` resolves to the SAME commit as HEAD -- the comparison is
    #: structurally impossible, not merely undecided (T-1678). This is the
    #: "committed straight to main" degenerate case: `base_ref` (a branch
    #: name like `"main"`, or a merge-base computed against it) turns out
    #: to already point AT the fix commit under test, so "run the repro
    #: test at base_ref" would just re-run it at the fix -- a vacuous,
    #: confirmatory-only comparison, never a real pre-fix reproduction.
    #: Distinct from `NO_VERDICT` (an infra failure) so the caller can log
    #: an explicit, honestly-worded UNRESOLVED explanation instead of a
    #: generic "could not check out" warning; treated identically to
    #: `NO_VERDICT` by every violation-producing caller (never a false
    #: PASSED_AT_PARENT violation, never a false FAILED_AT_PARENT pass).
    SAME_AS_HEAD = auto()
    #: `test_id` does not exist AT ALL in `base_ref`'s checked-out tree --
    #: pytest's own exit 5 ("no tests ran": collection succeeded, zero
    #: items matched the node id), never confused with the generic
    #: infra-failure NO_VERDICT (T-2025). This is the structural,
    #: BY-CONSTRUCTION consequence of `frob ticket land` squashing every
    #: worktree commit into ONE commit on main: once a ticket is landed,
    #: no ref in main's history ever contains that ticket's repro test
    #: WITHOUT its own fix already applied, because the test and the fix
    #: land together, atomically, in the same commit. Re-running
    #: `--check-repro` against any post-land ref for a newly-added test is
    #: therefore not merely inconclusive, it is IMPOSSIBLE by
    #: construction -- distinct from `NO_VERDICT` (a genuine infra
    #: failure that a retry or a different environment might resolve) so
    #: the caller can say exactly that instead of the generic "could not
    #: even collect" wording, which reads like a transient, maybe-
    #: retryable failure when it is actually a permanent one for this
    #: `test_id`/`base_ref` pair. Treated identically to `NO_VERDICT` by
    #: every violation-producing caller (never a false PASSED_AT_PARENT
    #: violation, never a false FAILED_AT_PARENT pass) -- this is a
    #: messaging refinement, not a new gating behavior. A caller with a
    #: genuinely earlier commit where the test predates the fix (e.g. a
    #: worktree branch's own pre-land, pre-squash commit, still reachable
    #: before the worktree is removed -- see T-2021's own evidence for the
    #: technique) passes that commit as an explicit `--base-ref` and gets
    #: a real `FAILED_AT_PARENT`/`PASSED_AT_PARENT` verdict as before;
    #: this outcome only fires when no such commit is reachable, which is
    #: unconditionally true for `base_ref="main"` (the default) against
    #: any ticket that has already landed.
    TEST_ABSENT_AT_PARENT = auto()


# frob:ticket T-1929
# frob:doc docs/modules/tickets.md#public-api
#: Public alias for `_BugReproOutcome` (T-1929): an on-demand caller
#: outside this module (`frob.app.ticket_runner._verify`'s validate-at-
#: designate check, `frob ticket evidence --check-repro`) needs to inspect
#: which of the seven outcomes `bug_repro_outcome_at_ref` returned --
#: FAILED_AT_PARENT is the only acceptable one to treat as a genuine
#: repro; PASSED_AT_PARENT, NO_VERDICT, (T-2480) TIMEOUT, SAME_AS_HEAD,
#: and (T-2025) TEST_ABSENT_AT_PARENT must never be silently treated as
#: a pass by any caller.
BugReproOutcome = _BugReproOutcome


# frob:tests \
# tests/test_gates_mutation_evidence.py::TestBug002Waiver.test_reason_present_suppresses
# frob:tests tests/test_gates_mutation_evidence.py::TestBug002Waiver.test_bare_directive_without_reason_does_not_suppress  # noqa: E501
def _bug002_waiver_reason(ticket: Ticket) -> str | None:
    """The `reason="..."` text of a `frob:waive BUG002 reason="..."` line
    found anywhere in `ticket.body`, or `None` if no such (well-formed)
    waiver is present. See `_BUG002_WAIVER_RE`'s comment for why this scans
    the ticket body directly instead of going through `frob.gates._waive`.

    T-2218: skips any match sitting inside a quoted range (`_quoted_char_
    ranges` -- a fenced/indented code block, blockquote, or inline code
    span), so a ticket that merely DISCUSSES the waiver mechanism in
    prose (quoting the directive as an example) is never mistaken for
    one that DECLARES it; the first non-quoted match still wins."""
    from frob.gates._mutation_evidence import (  # noqa: PLC0415
        _is_quoted,
        _quoted_char_ranges,
    )

    quoted = _quoted_char_ranges(ticket.body)
    for match in _BUG002_WAIVER_RE.finditer(ticket.body):
        if not _is_quoted(match.start(), quoted):
            return match.group(1)
    return None


# frob:ticket T-2870
def _bug002_malformed_waiver(ticket: Ticket) -> str | None:
    """T-2870: a short human-readable description of why a `frob:waive
    BUG002 ...` occurrence in `ticket.body` did NOT parse as a well-formed
    waiver, or `None` if either no such occurrence exists at all (nothing
    was ever attempted -- not this function's concern) or every occurrence
    parsed cleanly (`_bug002_waiver_reason` already returned it).

    Distinguishes "no waiver attempted" from "a waiver was attempted here
    and silently failed to parse" the same way `_bug002_waiver_reason`
    finds a WELL-formed one: scan every `_BUG002_WAIVER_CANDIDATE_RE`
    shape-match, skip anything inside a quoted range (T-2218's own
    discussed-not-declared exclusion, reused identically here), and check
    whether `_BUG002_WAIVER_RE`'s strict grammar also matches starting at
    that exact same offset. The two most likely mismatches, both measured
    incidents or their direct siblings: `reason=` with no opening `"` at
    all (a bare, unquoted value), and `reason="` opened but never closed
    anywhere in the rest of the body."""
    from frob.gates._mutation_evidence import (  # noqa: PLC0415
        _is_quoted,
        _quoted_char_ranges,
    )

    quoted = _quoted_char_ranges(ticket.body)
    well_formed_starts = {
        match.start() for match in _BUG002_WAIVER_RE.finditer(ticket.body)
    }
    for candidate in _BUG002_WAIVER_CANDIDATE_RE.finditer(ticket.body):
        if _is_quoted(candidate.start(), quoted):
            continue
        if candidate.start() in well_formed_starts:
            continue
        end = candidate.start() + 80
        snippet = ticket.body[candidate.start() : end].splitlines()[0]
        return f'{snippet!r} does not match the required reason="..." shape'
    return None


# frob:tests tests/test_gates_mutation_evidence.py::TestNoBehaviorChange.test_reason_present_recognized  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestNoBehaviorChange.test_bare_directive_without_reason_not_recognized  # noqa: E501
def _no_behavior_change_reason(ticket: Ticket) -> str | None:
    """The `reason="..."` text of a `frob:no-behavior-change reason="..."`
    line found anywhere in `ticket.body` (T-1616), or `None` if absent.
    Same body-text-scan rationale as `_bug002_waiver_reason` immediately
    above -- `tickets.md` is excluded from `frob.graph`'s doc/source walk,
    so this directive can only ever live here, scanned directly.

    T-2218: same quoted-range skip as `_bug002_waiver_reason` -- a match
    inside a fenced/indented code block, blockquote, or inline code span
    is a quoted example, not a live directive."""
    from frob.gates._mutation_evidence import (  # noqa: PLC0415
        _is_quoted,
        _quoted_char_ranges,
    )

    quoted = _quoted_char_ranges(ticket.body)
    for match in _NO_BEHAVIOR_CHANGE_RE.finditer(ticket.body):
        if not _is_quoted(match.start(), quoted):
            return match.group(1)
    return None


# frob:ticket T-2193
# frob:tests tests/test_gates_mutation_evidence.py::TestMustStillPassControls.test_single_directive_extracted  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestMustStillPassControls.test_multiple_directives_extracted  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestMustStillPassControls.test_no_directive_is_empty  # noqa: E501
def _must_still_pass_controls(ticket: Ticket) -> tuple[str, ...]:
    """Every `frob:must-still-pass NODE-ID` pytest node id declared in
    `ticket.body` (T-2193), in the order they appear. Empty tuple when no
    such directive is present -- this control is opt-in, an EXPLICIT,
    author-named designation (mirroring `--designate-repro`'s own
    explicit-not-inferred posture, per this ticket's own acceptance
    criteria), never auto-derived from the evidence set or from the
    suite passing.

    T-2218: same quoted-range skip as `_bug002_waiver_reason` -- a
    `frob:must-still-pass NODE-ID` shown as a quoted example (fenced/
    indented code block, blockquote, inline code span) is never treated
    as a declared control; only non-quoted matches contribute NODE-IDs,
    in the order they appear (unchanged ordering contract)."""
    from frob.gates._mutation_evidence import (  # noqa: PLC0415
        _is_quoted,
        _quoted_char_ranges,
    )

    quoted = _quoted_char_ranges(ticket.body)
    return tuple(
        match.group(1)
        for match in _MUST_STILL_PASS_RE.finditer(ticket.body)
        if not _is_quoted(match.start(), quoted)
    )


# frob:tests tests/test_gates_mutation_evidence.py::TestDesignatedReproTest.test_first_pytest_node_id_is_designated  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestDesignatedReproTest.test_no_pytest_evidence_is_none  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestDesignatedReproTest.test_explicit_designation_wins_over_bind_order  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestDesignatedReproTest.test_explicit_designation_not_in_evidence_falls_back_to_positional  # noqa: E501
def _designated_repro_test(ticket: Ticket) -> str | None:
    """The single evidence test BUG002 re-runs at the parent commit
    (T-1670): `ticket.designated_repro_test` if explicitly set (via `frob
    ticket evidence <id> --designate-repro`) AND still present in
    `ticket.evidence` (a designation whose id was since `--replace`d or
    dropped falls back to the positional default below, rather than
    silently checking a test no longer bound at all); otherwise the FIRST
    pytest-node-id-shaped entry (`path::name`, excluding `cmd:` entries --
    same shape `frob.tickets._mutation_evidence._evidence_test_ids`
    filters to) in `ticket.evidence`, deterministic and cheap (T-1421's
    cost constraint: check ONE test at ONE prior commit, never the whole
    bound evidence set).

    T-1670's whole point: before `designated_repro_test` existed, this was
    ALWAYS the positional-first match, an invisible bind-ORDER dependency
    nothing in `frob ticket evidence` surfaced at bind time -- an agent
    who bound a pre-existing (already-passing-everywhere) test first and
    its real new repro test second got BUG002 checking the wrong one,
    passing at parent, and refusing land for a reason unrelated to the
    actual evidence quality. Explicit designation removes the ordering
    dependency; the positional fallback stays for every ticket that never
    designates one, so pre-T-1670 behavior is unchanged by default.

    `None` when the ticket has no pytest evidence at all -- nothing to
    check, matching `check_ticket_mutation_evidence`'s own "no pytest
    evidence, nothing to check" posture."""
    designated = ticket.designated_repro_test
    if designated is not None and designated in ticket.evidence:
        return designated
    for entry in ticket.evidence:
        if "::" in entry and not entry.startswith("cmd:"):
            return entry
    return None


# frob:tests \
# tests/test_gates_mutation_evidence.py::TestBugReproAtRef.test_same_as_head_is_vacuous
def _resolve_sha(root: Path, ref: str) -> str | None:
    """`git rev-parse <ref>`, trimmed, or `None` on any spawn/exit failure
    -- split out purely so `_bug_repro_outcome_at_ref`'s vacuous-comparison
    check (T-1678) has a single place to resolve both `HEAD` and
    `base_ref` to comparable commit shas before deciding whether to spend
    a real checkout+subprocess on a comparison that cannot mean anything."""
    resolved = run_argv(("git", "-C", str(root), "rev-parse", ref))
    if resolved.is_err or resolved.danger_ok.returncode != 0:
        return None
    return resolved.danger_ok.stdout.strip()


# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproAtRef.test_exec_disabled_is_no_verdict  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproAtRef.test_worktree_add_failure_is_no_verdict  # noqa: E501
# frob:tests \
# tests/test_gates_mutation_evidence.py::TestBugReproAtRef.test_same_as_head_is_vacuous
def _bug_repro_outcome_at_ref(
    root: Path, test_id: str, base_ref: str, *, timeout_s: float = _BUG_REPRO_TIMEOUT_S
) -> _BugReproOutcome:
    """Run `test_id` (a single pytest node id) against `base_ref`'s
    checked-out content, in isolation from `root`'s own working tree, and
    classify the result.

    Cheaper than a full second `uv run`/reinstall: a plain `git worktree
    add --detach` checkout of `base_ref` (no build step -- reuses
    `root`'s already-built native extensions and installed venv) with
    `PYTHONPATH` pointed at the checkout's own `src/` so the subprocess
    imports the PARENT COMMIT's Python source instead of `root`'s
    editable-install path. This only proves out for pure-Python changes
    (the five real T-1421 incidents were all exactly this shape -- an
    added guard/parameter never wired to a caller); a parent-commit change
    that also touched compiled native code is exactly the "genuinely
    cannot reproduce in this harness" case the `frob:waive BUG002`
    escape hatch exists for (see its docstring above), surfaced here as
    `NO_VERDICT` via a non-{0,1} pytest exit (a collection/import error),
    never mistaken for a real pass.
    """
    if not exec_enabled():
        _log.warning(
            "BUG002: exec disabled via kill switch, no repro-at-parent verdict for %s",
            test_id,
        )
        return _BugReproOutcome.NO_VERDICT
    head_sha = _resolve_sha(root, "HEAD")
    base_sha = _resolve_sha(root, base_ref)
    if head_sha is not None and base_sha is not None and head_sha == base_sha:
        _log.warning(
            "BUG002: base_ref %r resolves to HEAD itself (%s) -- the fix "
            "commit under test IS the commit the repro would run against, "
            "so no pre-fix comparison is possible; reporting UNRESOLVED "
            "for %s rather than a verdict computed against itself. This "
            "is the direct-commit-to-main shape (T-1678): the pre-fix "
            "state was never a separate ref this check can reach",
            base_ref,
            head_sha,
            test_id,
        )
        return _BugReproOutcome.SAME_AS_HEAD
    scratch = Path(tempfile.mkdtemp(prefix="frob-bug002-"))
    worktree = scratch / "wt"
    try:
        if not _checkout_bug_repro_worktree(root, worktree, base_ref, test_id):
            return _BugReproOutcome.NO_VERDICT
        return _run_designated_test(worktree, test_id, timeout_s)
    finally:
        _remove_bug_repro_worktree(root, worktree)
        shutil.rmtree(scratch, ignore_errors=True)


# frob:ticket T-1929
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/gates/test_bug_repro_at_ref_public.py::TestBugReproOutcomeAtRefPublic.test_wraps_the_private_classifier  # noqa: E501
def bug_repro_outcome_at_ref(
    root: Path,
    test_id: str,
    base_ref: str = "main",
    *,
    timeout_s: float | None = None,
) -> _BugReproOutcome:
    """Public entrypoint (T-1929) exposing `_bug_repro_outcome_at_ref`'s
    parent-commit repro classification to callers OUTSIDE this module --
    `frob.app.ticket_runner._verify`'s validate-at-designate check
    (`--designate-repro`, requirement A) and `frob ticket evidence
    --check-repro`'s on-demand read-only path (requirement B) both call
    this SAME function rather than reaching into the private helper
    directly, so there remains exactly one place that spawns and
    classifies the repro subprocess -- do not add a second copy of this
    machinery; `bug_repro_violations` below is the land/close-time
    consumer of the identical classification and must keep using it too.

    T-2480: `timeout_s`, `None` by default, overrides
    `_BUG_REPRO_TIMEOUT_S` for THIS call only -- a caller whose repro
    test is known to be design/architecture-level (inherently slower,
    since demonstrating the defect means elaborating the whole model)
    can raise the budget explicitly instead of the check silently
    turning "did not finish in time" into a `NO_VERDICT` that reads
    exactly like "does not reproduce". `bug_repro_violations` (the land/
    close-time consumer) deliberately does NOT expose this parameter --
    a per-ticket override at gate time would let a slow, never-actually-
    verified test simply wait longer instead of surfacing TIMEOUT for a
    human to act on; the override is for the interactive/on-demand paths
    (`--check-repro`, `--designate-repro`) where a caller is actively
    watching and can choose to raise it.

    Deliberately a thin, no-logic wrapper otherwise: it does not decide
    anything about ticket kind, waivers, or severity -- callers get the
    raw `_BugReproOutcome` (its public alias `BugReproOutcome`, above)
    and decide what to do with FAILED_AT_PARENT / PASSED_AT_PARENT /
    NO_VERDICT / TIMEOUT / SAME_AS_HEAD for their own purpose."""
    resolved_timeout = timeout_s if timeout_s is not None else _BUG_REPRO_TIMEOUT_S
    return _bug_repro_outcome_at_ref(
        root, test_id, base_ref, timeout_s=resolved_timeout
    )


# frob:ticket T-1929
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/gates/test_bug_repro_at_ref_public.py::TestDesignatedReproTestPublic.test_wraps_the_private_resolver  # noqa: E501
def designated_repro_test(ticket: Ticket) -> str | None:
    """Public wrapper (T-1929) around `_designated_repro_test`, for a
    caller outside this module that needs to resolve WHICH evidence id
    BUG002 would check without duplicating the "explicit designation,
    falling back to first pytest-node-id evidence" rule -- `frob ticket
    evidence --check-repro` (no NODE-ID given) uses this to pick the same
    test `bug_repro_violations` would have checked at land/close time."""
    return _designated_repro_test(ticket)


def _checkout_bug_repro_worktree(
    root: Path, worktree: Path, base_ref: str, test_id: str
) -> bool:
    """`git worktree add --detach worktree base_ref`'s spawn-and-classify
    half, split out of `_bug_repro_outcome_at_ref` (ARCH103: keep I/O and
    branching apart). `True` on a clean checkout; `False` (logged) on any
    spawn/exit failure -- the caller degrades that to `NO_VERDICT`."""
    added = run_argv(
        (
            "git",
            "-C",
            str(root),
            "worktree",
            "add",
            "--detach",
            str(worktree),
            base_ref,
        ),
        timeout_s=_BUG_REPRO_WORKTREE_TIMEOUT_S,
    )
    if added.is_err or added.danger_ok.returncode != 0:
        _log.warning(
            "BUG002: could not check out %s at %s for repro check (%s) -- no verdict",
            base_ref,
            test_id,
            added.danger_ok.stderr if added.is_ok else added.danger_err,
        )
        return False
    return True


# frob:ticket T-2480
# frob:ticket T-2495
def _spawn_designated_test(
    worktree: Path, test_id: str, timeout_s: float
) -> Result[subprocess.CompletedProcess[str], _BugReproOutcome]:
    """`_run_designated_test`'s spawn-only half (ARCH103 split, T-2480):
    launch `test_id` in `worktree` via the CURRENT interpreter,
    `PYTHONPATH`-pointed at `worktree/src` so imports resolve to the
    checked-out parent-commit source. Returns `Ok(CompletedProcess)` on
    any real exit, or `Err(_BugReproOutcome)` for the two ways a REAL
    exit was never reached: `TIMEOUT` (T-2480) or `NO_VERDICT` (kill
    switch / spawn refusal) -- the caller classifies a real exit's
    return code; this function only ever returns those two outcomes on
    its `Err` side, never a code-based one.

    Called DIRECTLY via `guarded_subprocess_run` (still kill-switch-
    gated, `frob.gitio.run_argv`'s own underlying primitive) rather than
    through `run_argv` itself -- `run_argv` catches `subprocess.
    TimeoutExpired` internally and collapses it into the SAME `Err(
    GitError.GitFailed)` a spawn refusal or an `OSError` produces, so a
    caller downstream of `run_argv` cannot tell "hit the time budget"
    apart from "could not spawn at all" -- exactly the ambiguity T-2480
    exists to close. Catching the timeout HERE, before it would be
    collapsed, is what makes `TIMEOUT` a real, distinct outcome instead
    of another shade of `NO_VERDICT`."""
    env = dict(os.environ)
    src = str(worktree / "src")
    env["PYTHONPATH"] = (
        src if not env.get("PYTHONPATH") else src + os.pathsep + env["PYTHONPATH"]
    )
    argv = (sys.executable, "-m", "pytest", test_id, "-q", "-p", "no:cacheprovider")
    try:
        guarded = guarded_subprocess_run(
            list(argv),
            cwd=str(worktree),
            capture_output=True,
            timeout=timeout_s,
            text=True,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        _log.warning(
            "BUG002: repro run of %s exceeded its %gs budget -- TIMEOUT, "
            "not NO_VERDICT: this test may well genuinely reproduce the "
            "defect, it simply could not be MEASURED in time. Re-run with "
            "a larger --repro-timeout-s, or use --designate-repro-force "
            "with the timeout noted as the reason if the fail-at-parent/"
            "pass-at-fix shape has already been verified by hand",
            test_id,
            timeout_s,
        )
        return Err(_BugReproOutcome.TIMEOUT)
    if guarded.is_err:
        if guarded.danger_err is ProcessGuardError.ExecDisabled:
            _log.warning(
                "BUG002: exec disabled via kill switch, no repro-at-parent "
                "verdict for %s",
                test_id,
            )
        else:
            _log.warning(
                "BUG002: repro run of %s failed to spawn -- no verdict", test_id
            )
        return Err(_BugReproOutcome.NO_VERDICT)
    return Ok(guarded.danger_ok)


def _classify_designated_test_exit(
    result: subprocess.CompletedProcess[str], test_id: str
) -> _BugReproOutcome:
    """`_run_designated_test`'s exit-code-classification half (ARCH103
    split, T-2480, extracted unchanged from the pre-split function's own
    body): exit 0 -> `PASSED_AT_PARENT`; exit 1 (a genuine assertion/
    error failure) -> `FAILED_AT_PARENT`; any other exit whose output
    shows ZERO tests were collected (`test_id` does not exist in this
    tree at all, T-2025) -> `TEST_ABSENT_AT_PARENT`; anything else
    (collection error, missing native extension) -> `NO_VERDICT`, never
    guessed at as a pass or a fail.

    T-2025: the "test does not exist here" case does NOT map to one fixed
    exit code -- measured directly, pytest 9.0.3 returns 4 ("not found:
    NODEID, no match in any of [...]") for a missing method on an
    existing class in a minimal synthetic repo, but this repo's own real
    historical commits (T-1546, T-1907, ...) measured exit 5 for the
    identical shape (class exists, method does not) once this repo's own
    `tests/conftest.py`/plugin set are involved. Branching on the exit
    code alone would silently miss one or the other depending on
    environment. Checked instead, in priority order: (1) this repo's own
    `tests/conftest.py::pytest_sessionfinish` always prints
    `SUITE-RESULT: exitstatus=N collected=0 ...` when nothing was
    collected -- present and confirmed in the checked-out worktree
    whenever that hook exists at `base_ref` (which every real historical
    ref this function is ever called against does, T-1596 predates
    BUG002 itself); (2) pytest's own builtin "no tests ran" summary line,
    kept as a fallback for the rare checkout that predates T-1596's hook
    or otherwise lacks it -- confirmed present alongside the custom line
    in the same measured run, so this is genuinely a fallback, not a
    guess."""
    rc = result.returncode
    if rc == 0:
        return _BugReproOutcome.PASSED_AT_PARENT
    if rc == 1:
        return _BugReproOutcome.FAILED_AT_PARENT
    combined_output = result.stdout + result.stderr
    zero_collected = bool(re.search(r"\bcollected=0\b", combined_output))
    if zero_collected or "no tests ran" in combined_output:
        _log.warning(
            "BUG002: repro run of %s exited %d at parent -- pytest reports "
            "'no tests ran': %s does not exist in this tree at all (T-2025: "
            "systematically true for EVERY already-landed ticket's own "
            "post-land history, since `frob ticket land` squashes the "
            "repro test and its fix into one atomic commit -- see "
            "docs/modules/tickets.md#check-repro-post-land-limitation-t-2025) "
            "-- no verdict",
            test_id,
            rc,
            test_id,
        )
        return _BugReproOutcome.TEST_ABSENT_AT_PARENT
    _log.warning(
        "BUG002: repro run of %s exited %d at parent (not a plain pass/fail -- "
        "likely a collection error, e.g. a native extension the parent commit's "
        "isolated checkout never built) -- no verdict",
        test_id,
        rc,
    )
    return _BugReproOutcome.NO_VERDICT


def _run_designated_test(
    worktree: Path, test_id: str, timeout_s: float
) -> _BugReproOutcome:
    """`_bug_repro_outcome_at_ref`'s spawn-and-classify half (ARCH103
    split into `_spawn_designated_test` + `_classify_designated_test_exit`
    above, T-2480) -- this function is now just their composition, same
    posture as `_try_check_delta_via_daemon`'s own split precedent."""
    spawned = _spawn_designated_test(worktree, test_id, timeout_s)
    if spawned.is_err:
        return spawned.danger_err
    return _classify_designated_test_exit(spawned.danger_ok, test_id)


def _remove_bug_repro_worktree(root: Path, worktree: Path) -> None:
    """Best-effort `git worktree remove --force`, logged but never raised
    -- `_bug_repro_outcome_at_ref`'s `finally` already falls back to a
    plain `shutil.rmtree` of the scratch dir, so a failure here just means
    the worktree's git-side registration lingers until the next `frob
    worktree sweep` / `git worktree prune`, not a lost repro verdict."""
    removed = run_argv(
        ("git", "-C", str(root), "worktree", "remove", "--force", str(worktree)),
        timeout_s=_BUG_REPRO_WORKTREE_TIMEOUT_S,
    )
    if removed.is_err or removed.danger_ok.returncode != 0:
        _log.warning("BUG002: could not remove scratch worktree %s", worktree)


# frob:waive DUP001 reason="coincidental structural resemblance only: \
# remediation/message-builder functions across 8 unrelated subsystems (doctor \
# version-skew, BUG002 repro-evidence messages, mutation evidence, strata waive, \
# deploy generate, scaffold managed, dup rules formatting, ticket close-cmd hints) -- \
# no shared domain, independently evolving, spot-checked per T-2966"
def _bug002_message(ticket_id: str, test_id: str, base_ref: str) -> str:
    """BUG002's refusal message: names the designated test, the parent ref
    it was re-run against, and both documented remedies -- fix the
    reproduction (bind evidence that actually fails before the fix), or
    the `frob:waive BUG002 reason="..."` escape hatch for a genuinely
    unreproducible defect."""
    return (
        f"BUG002: {ticket_id}'s designated reproduction test {test_id!r} "
        f"PASSED at the parent commit ({base_ref}) -- this evidence does "
        f"not prove the defect it describes was actually fixed, only that "
        f"new code exists. Remedy: (1) bind evidence that genuinely fails "
        f"at {base_ref} and passes at the fix (a test that reaches the "
        f"real caller/wiring the defect was about), (2) if this is really "
        f"a refactor/deletion with no intended behavior change (T-1616), "
        f'add `frob:no-behavior-change reason="..."` to the ticket body '
        f"-- BUG002 will then require the OPPOSITE (the test must PASS at "
        f"{base_ref}) instead of skipping the check, or (3) if this defect "
        f"genuinely cannot be reproduced in a test (a nondeterministic "
        f"crash, an environment the suite cannot create, a ledger/doc "
        f"correction filed as kind=bug), add `frob:waive BUG002 "
        f'reason="..."` to the ticket body explaining why, in the same '
        f"spirit as `frob ticket land --skip-mutation-evidence`."
    )


# frob:waive DUP001 reason="coincidental structural resemblance only: \
# remediation/message-builder functions across 8 unrelated subsystems (doctor \
# version-skew, BUG002 repro-evidence messages, mutation evidence, strata waive, \
# deploy generate, scaffold managed, dup rules formatting, ticket close-cmd hints) -- \
# no shared domain, independently evolving, spot-checked per T-2966"
def _no_behavior_change_message(ticket_id: str, test_id: str, base_ref: str) -> str:
    """T-1616's inverted BUG002 message: fires when a ticket claims `frob:
    no-behavior-change` but its own designated evidence test FAILED at the
    parent commit -- the exact opposite failure mode of the ordinary
    `_bug002_message`, and it means the claim itself is false: something
    behavioral DID change, contradicted by the ticket's own repro."""
    return (
        f"BUG002: {ticket_id} claims `frob:no-behavior-change` but its "
        f"designated evidence test {test_id!r} FAILED at the parent commit "
        f"({base_ref}) -- that contradicts the claim: a test that fails "
        f"before this ticket's change and (presumably) passes after it "
        f"means something DID behave differently, not nothing. Remedy: "
        f"(1) confirm the change really is behavior-preserving and bind "
        f"evidence that passes at both {base_ref} and the fix (a "
        f"characterization test of the touched seam, not a new-behavior "
        f"test), or (2) if this genuinely is a behavioral fix, drop the "
        f"`frob:no-behavior-change` claim and let BUG002's ordinary "
        f"defect-repro check apply instead."
    )


# frob:enforces CHK-GATE-BUG002
# frob:doc \
# docs/modules/gates.md#bug002-t-1421-a-bug-ticket-must-prove-the-defect-no-longer-repr\
# oduces
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolations.test_non_bug_kind_never_checked  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolations.test_no_pytest_evidence_no_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolations.test_waived_with_reason_no_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolations.test_passed_at_parent_is_error_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolations.test_failed_at_parent_no_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolations.test_no_verdict_no_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolationsNoBehaviorChange.test_passed_at_parent_no_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolationsNoBehaviorChange.test_failed_at_parent_is_error_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolationsNoBehaviorChange.test_no_verdict_no_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugRepro.test_reconstructed_uncalled_guard_passes_at_both_is_refused kind="integration"  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugRepro.test_reconstructed_wired_guard_fails_at_parent_is_permitted kind="integration"  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugRepro.test_fix_committed_direct_to_main_is_unresolved_not_refused kind="integration"  # noqa: E501
# frob:ticket T-1678
# frob:ticket T-2883
def bug_repro_violations(
    root: Path, ticket: Ticket, base_ref: str = "main"
) -> tuple[Violation, ...]:
    """BUG002 (T-1421): a `bug`/`security`-kind ticket's designated
    evidence test must have genuinely FAILED at `base_ref` (the ticket's
    parent commit) -- the mechanically checkable form of "the defect no
    longer reproduces", complementing TEST016 (`mutation_evidence_
    violations` above) rather than duplicating it: TEST016 proves the
    ticket's OWN diff is mutation-detectable by its bound evidence, which
    is silent about whether anything actually CALLS the changed code
    (`frob.tickets._evidence`'s `own_obligations_clean`/T-1384 class of
    incident -- new code was mutation-detectable, but no caller reached
    it, so TEST016 passed while the defect stayed live on `main`). This
    rule instead re-runs the SAME evidence test against the commit BEFORE
    the ticket's changes and checks it genuinely fails there -- something
    TEST016's diff-scoped mutation pass cannot see at all, since an absent
    caller has no mutant to kill or survive.

    ERROR severity always (this rule only ever fires for `bug`/`security`
    kind, both already ERROR-severity for TEST016 -- see module docstring
    for why those two kinds get the harder gate). `()` (no violation)
    whenever: the ticket is not `bug`/`security`-kind; it has no
    pytest-node-id evidence yet (nothing to check); a `frob:waive BUG002
    reason="..."` override is present in the ticket body (logged loudly,
    T-1421's required escape hatch); or the repro run at `base_ref`
    produced `FAILED_AT_PARENT` (the honest, expected case) or
    `NO_VERDICT` (an infra/kill-switch degrade -- never a false
    violation, mirroring TEST016's own `ExecDisabled` posture)."""
    from frob.gates._mutation_evidence import _ERROR_KINDS  # noqa: PLC0415

    if ticket.kind not in _ERROR_KINDS:
        return ()
    waiver_reason = _bug002_waiver_reason(ticket)
    if waiver_reason is not None:
        _log.warning(
            "BUG002: %s waived via frob:waive BUG002 reason=%r -- no "
            "repro-at-parent check run",
            ticket.id,
            waiver_reason,
        )
        return ()
    # T-2870: a `frob:waive BUG002` was ATTEMPTED but could not be parsed
    # (unquoted/unterminated reason=) -- report it LOUDLY, naming the
    # ticket and the offending text, rather than silently falling through
    # to "no waiver present" the way this used to (T-2857 mode 2's
    # measured incident: the author believed the ticket was waived, the
    # land proceeded as though it were not).
    malformed = _bug002_malformed_waiver(ticket)
    if malformed is not None:
        _log.warning(
            "BUG002: %s has a frob:waive BUG002 directive that does NOT "
            "parse and is therefore NOT applied (%s) -- BUG002 runs as "
            "though no waiver were present; fix the reason=\"...\" "
            "quoting to actually suppress this check",
            ticket.id,
            malformed,
        )
    test_id = _designated_repro_test(ticket)
    if test_id is None:
        _log.debug(
            "BUG002: %s has no pytest-node-id evidence yet, nothing to check",
            ticket.id,
        )
        return ()
    outcome = _bug_repro_outcome_at_ref(root, test_id, base_ref)

    # T-1616: a `frob:no-behavior-change reason="..."` claim SWAPS the
    # obligation rather than skipping it -- refactor/deletion-shaped work
    # whose entire point is that behavior did NOT change cannot honestly
    # satisfy "the designated test fails at the parent" (that would prove
    # the OPPOSITE of the claim). Instead: the designated test must PASS
    # at the parent (unchanged there too); a genuine FAILED_AT_PARENT
    # falsifies the claim and is the violation. NO_VERDICT still degrades
    # to no violation either way -- an infra/kill-switch gap is not
    # evidence against either claim.
    no_behavior_change_reason = _no_behavior_change_reason(ticket)
    if no_behavior_change_reason is not None:
        _log.warning(
            "BUG002: %s claims frob:no-behavior-change reason=%r -- "
            "checking the INVERTED obligation (designated test must PASS "
            "at the parent)",
            ticket.id,
            no_behavior_change_reason,
        )
        if outcome is not _BugReproOutcome.FAILED_AT_PARENT:
            return ()
        return (
            Violation(
                rule="BUG002",
                severity=Severity.ERROR,
                file="tickets.md",
                line=0,
                message=_no_behavior_change_message(ticket.id, test_id, base_ref),
            ),
        )

    if outcome is not _BugReproOutcome.PASSED_AT_PARENT:
        return ()
    return (
        Violation(
            rule="BUG002",
            severity=Severity.ERROR,
            file="tickets.md",
            line=0,
            message=_bug002_message(ticket.id, test_id, base_ref),
        ),
    )


# frob:waive DUP001 reason="coincidental structural resemblance only: \
# remediation/message-builder functions across 8 unrelated subsystems (doctor \
# version-skew, BUG002 repro-evidence messages, mutation evidence, strata waive, \
# deploy generate, scaffold managed, dup rules formatting, ticket close-cmd hints) -- \
# no shared domain, independently evolving, spot-checked per T-2966"
def _must_still_pass_broke_at_fix_message(ticket_id: str, test_id: str) -> str:
    """BUG003 (T-2193): the designated capability control genuinely
    FAILS at the ticket's own fix -- the exact silent-capability-loss
    shape this control exists to catch (a narrowing fix that
    over-corrected until it accepts/matches nothing)."""
    return (
        f"BUG003: {ticket_id}'s must-still-pass control {test_id!r} FAILS "
        f"at this ticket's own fix -- the capability it asserts was still "
        f"exercised did not survive this change. This is the exact shape "
        f"a narrowing fix (resolution/matching/filtering/gating) can "
        f"over-correct into: the negative-direction evidence (BUG002/"
        f"TEST016) can be perfectly clean while the positive case is "
        f"silently disabled. Remedy: fix the narrowing so this control "
        f"passes again, or if the control test itself no longer applies, "
        f"pick a different `frob:must-still-pass NODE-ID` that genuinely "
        f"characterizes the surviving capability."
    )


# frob:waive DUP001 reason="coincidental structural resemblance only: \
# remediation/message-builder functions across 8 unrelated subsystems (doctor \
# version-skew, BUG002 repro-evidence messages, mutation evidence, strata waive, \
# deploy generate, scaffold managed, dup rules formatting, ticket close-cmd hints) -- \
# no shared domain, independently evolving, spot-checked per T-2966"
def _must_still_pass_never_passed_message(ticket_id: str, test_id: str) -> str:
    """BUG003: the designated control did not even PASS at the parent
    commit -- it cannot prove "the fix kept this working" because it was
    never established as working in the first place. A misconfigured
    designation (the author picked the wrong test), not a real capability
    regression -- still refused, since a control that cannot prove its
    own claim is not evidence."""
    return (
        f"BUG003: {ticket_id}'s must-still-pass control {test_id!r} did "
        f"NOT pass at the parent commit either -- it cannot serve as a "
        f"MUST-STILL-PASS control, since there is no established "
        f"'working before' state for it to prove survived the fix. "
        f"Remedy: designate a test that genuinely passed before this "
        f"ticket's change and exercises the capability the narrowing "
        f"fix must not silently disable."
    )


# frob:ticket T-2193
# frob:enforces CHK-GATE-BUG003
# frob:doc docs/modules/tickets-landing.md#mutation-evidence-obligation-test016-t-0755
# frob:tests tests/test_gates_mutation_evidence.py::TestMustStillPassViolations.test_no_directive_no_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestMustStillPassViolations.test_passes_at_both_no_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestMustStillPassViolations.test_fails_at_fix_is_error_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestMustStillPassViolations.test_never_passed_at_parent_is_error_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestMustStillPassViolations.test_unresolvable_parent_degrades_to_no_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestMustStillPassViolations.test_unresolvable_fix_degrades_to_no_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestMustStillPassViolations.test_multiple_directives_each_checked  # noqa: E501
def must_still_pass_violations(
    root: Path, ticket: Ticket, base_ref: str = "main"
) -> tuple[Violation, ...]:
    """BUG003 (T-2193): the positive-direction control BUG002/TEST016
    have no counterpart for. Both of those only ever prove a NEGATIVE
    claim (a repro that failed before the fix, a mutant this ticket's
    evidence kills) -- silent about whether the capability a narrowing
    fix touches still runs at all. Three measured instances this session
    (T-2156, T-2177, `frob cycle`'s own src-layout gap -- see this
    ticket's own body) all passed BUG002/TEST016 while the underlying
    capability was, or could have been, entirely disabled.

    For each `frob:must-still-pass NODE-ID` declared in `ticket.body`
    (`_must_still_pass_controls`, opt-in and explicit -- never inferred
    from the evidence set or the suite passing, per this ticket's own
    acceptance criteria): the SAME node id is run twice, once against
    `root`'s current tree (the fix) and once against `base_ref` (the
    parent, via the same `_bug_repro_outcome_at_ref` machinery BUG002
    already uses -- no second checkout mechanism invented). A genuine
    violation fires in exactly two shapes, both ERROR (silent capability
    loss is never advisory-tier): the control FAILS at the fix (the
    capability broke -- `_must_still_pass_broke_at_fix_message`), or the
    control never PASSED at the parent either (a misconfigured
    designation that cannot prove anything --
    `_must_still_pass_never_passed_message`). Every other combination
    (both pass; either side is unresolvable -- `NO_VERDICT`/
    `SAME_AS_HEAD`/`TEST_ABSENT_AT_PARENT`) degrades to no violation,
    mirroring BUG002's own infra-failure posture: an unmeasurable
    comparison is never guessed at as either a pass or a fail.

    Not restricted to `bug`/`security` kind (unlike BUG002/TEST016):
    the narrowing-fix shape this control targets is not kind-specific,
    and the directive itself is the explicit opt-in -- absence of the
    directive is always `()`, for any kind."""
    violations: list[Violation] = []
    for test_id in _must_still_pass_controls(ticket):
        fix_outcome = _run_designated_test(root, test_id, _BUG_REPRO_TIMEOUT_S)
        if fix_outcome not in (
            _BugReproOutcome.PASSED_AT_PARENT,
            _BugReproOutcome.FAILED_AT_PARENT,
        ):
            # Unresolvable at the fix (collection error, missing native,
            # timeout) -- never guessed at either direction.
            continue
        if fix_outcome is _BugReproOutcome.FAILED_AT_PARENT:
            violations.append(
                Violation(
                    rule="BUG003",
                    severity=Severity.ERROR,
                    file="tickets.md",
                    line=0,
                    message=_must_still_pass_broke_at_fix_message(ticket.id, test_id),
                )
            )
            continue
        parent_outcome = _bug_repro_outcome_at_ref(root, test_id, base_ref)
        if parent_outcome is _BugReproOutcome.FAILED_AT_PARENT:
            violations.append(
                Violation(
                    rule="BUG003",
                    severity=Severity.ERROR,
                    file="tickets.md",
                    line=0,
                    message=_must_still_pass_never_passed_message(ticket.id, test_id),
                )
            )
        # PASSED_AT_PARENT (clean) and every other unresolvable outcome
        # (NO_VERDICT/SAME_AS_HEAD/TEST_ABSENT_AT_PARENT) both produce no
        # violation here -- an unmeasurable parent comparison is not
        # evidence against the control.
    return tuple(violations)


__all__ = [
    "bug_repro_violations",
    "must_still_pass_violations",
]
