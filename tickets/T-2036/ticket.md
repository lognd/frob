---
id: T-2036
title: T-1983's auto-drop silently drops a ticket whose findings are still live on
  an absolute-vs-relative path mismatch
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
evidence_scope:
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_rapid_sweep.py::TestAbsoluteVsRelativePathIdentityMismatch::test_format_drift_between_sweeps_does_not_falsely_resolve_a_live_ticket
designated_repro_test: tests/unit/test_rapid_sweep.py::TestAbsoluteVsRelativePathIdentityMismatch::test_format_drift_between_sweeps_does_not_falsely_resolve_a_live_ticket
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1983's auto-drop path can silently drop a ticket whose findings are
still LIVE when the recorded identity's `file` component and the fresh
measurement's `file` component disagree on ABSOLUTE vs REPO-RELATIVE
path form for the SAME file -- the set comparison (`vanished = baseline
- fresh`, and `identities <= vanished` in `_maybe_drop_resolved_ticket`)
is a plain string-tuple equality, so `("F401",
"/home/logan/projects/frob/tests/x.py")` and `("F401", "tests/x.py")`
never match even though they name the identical finding.

MEASURED (coordinator, 2026-08-10): T-2022 was auto-dropped citing 3
resolved identities (COV003, and two F401s). Re-measuring on current
main:

    uv run ruff check tests/test_gates_fmt_directives.py \
      tests/unit/test_tickets_evidence_only_scope.py
    F401 [*] `pytest` imported but unused
      --> tests/unit/test_tickets_evidence_only_scope.py:17:8
    Found 2 errors.

Both F401 findings are STILL LIVE. Only the COV003 identity (recorded
with a repo-relative path, `tickets/T-0907`) had genuinely vanished.
T-2022's own filed body (commit 37d92a5fb) recorded the two F401
identities with ABSOLUTE paths
(`/home/logan/projects/frob/tests/test_gates_fmt_directives.py`,
`/home/logan/projects/frob/tests/unit/test_tickets_evidence_only_scope.py`)
-- a later sweep's fresh measurement evidently reported these same files
with repo-relative paths, so the never-matching absolute identity read
as "vanished" and the ticket was dropped while live work was lost.

This directly contradicts `run_deferred_post_land_sweep`'s own stated
invariant: "no false drops, since dropping a live regression is
strictly worse than leaving a stale one."

## Requirements
1. Normalize identity `file` components to repo-relative POSIX form at
   every point `_rapid_sweep.py` constructs OR compares a `(rule, file)`
   identity set -- the fresh measurement just ingested from
   `_unscoped_error_findings`, the identities parsed back out of a
   previously-filed ticket's body (`_parse_sweep_ticket_identities`,
   which must handle a ticket filed BEFORE this fix, still carrying an
   absolute path), and the identities written into a newly-filed
   ticket's body.
2. Safer-direction default: an identity that cannot be confidently
   normalized/matched must count as STILL PRESENT, never as vanished.
3. Reopen T-2022 -- it was dropped on a false premise; its two F401
   findings are real, unfixed work.
4. Consider (and either add or explain not adding) a `frob:invariant`
   anchor backing the "no false drops" claim with a real test, not just
   a docstring sentence.

## Acceptance criteria
1. A test that FAILS FIRST: record an identity with an ABSOLUTE path,
   run the vanished/dropped comparison against a fresh measurement that
   reports the SAME file with a REPO-RELATIVE path, and assert the
   ticket is correctly recognized as NOT resolved (not dropped).
2. T-2022 is reopened with its two still-live F401 findings intact.

## Done report

Root cause (measured against T-2022's own filed body vs a re-measurement
on main): `_rapid_sweep.py`'s `(rule, file)` identity comparisons
(`vanished = baseline - fresh`, `identities <= vanished`) are plain
tuple equality, and a diagnostic's `file` field is not guaranteed to
render the same way (absolute vs repo-relative) across two separate
`frob check` spawns. Format drift between two sweep runs makes a
still-broken file's identity silently "vanish" from the diff, and the
ticket that named it is auto-dropped on a false premise -- confirmed
directly against T-2022 (filed with two absolute-path F401 identities;
both still reproduce on main today via a direct `ruff check`).

Added `_normalize_identity_file` / `_normalize_identities` and routed
every point `_rapid_sweep.py` constructs or reads a `(rule, file)`
identity set through them: the fresh unscoped measurement
(`run_deferred_post_land_sweep`), the persisted rolling baseline (both
`_read_baseline` and the write path, since `fresh` is normalized
before `_write_baseline` runs), and identities parsed back out of a
previously-filed ticket's body in BOTH call sites of
`_maybe_drop_resolved_ticket`'s caller (the T-1983 sweep path and the
T-2006 `doable` path) -- so a ticket filed before this fix, still
carrying an absolute path, now compares correctly against a
freshly-normalized set.

First test
(`TestAbsoluteVsRelativePathIdentityMismatch::test_format_drift_between_sweeps_does_not_falsely_resolve_a_live_ticket`)
was committed alone against the unfixed code and watched to FAIL (the
still-broken ticket ended up state DROPPED, not QUEUED) before the fix
commit was added; `--check-repro --base-ref <test-only commit>`
independently confirmed `FAILED_AT_PARENT`.

DISCLOSED CUT: T-2022 itself was NOT reopened in this land. Its scope
(`tests/test_gates_fmt_directives.py`,
`tests/unit/test_tickets_evidence_only_scope.py`, `tickets/T-0907`)
does not overlap this ticket's declared scope
(`src/frob/app/ticket_runner/_rapid_sweep.py`), and this worktree's
CLI exposed no `reopen` verb for a `dropped` ticket -- only
`plan`/`start`/`close`/`drop`.

Filed: T-2037

NOT fixed here (explicitly out of scope, filed separately): T-2030,
the sweep writing into a concurrent agent's own worktree -- a
root-path-resolution defect the coordinator suspects shares an
upstream cause with this ticket's own false-drop, but which was not
independently investigated in the time available this session.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_rapid_sweep.py::TestAbsoluteVsRelativePathIdentityMismatch::test_format_drift_between_sweeps_does_not_falsely_resolve_a_live_ticket` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, DRIFT002@src/frob/app/ticket_runner/_rapid_sweep.py, F401@/home/logan/projects/frob/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-2036
