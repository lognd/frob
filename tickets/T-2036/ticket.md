---
id: T-2036
title: T-1983's auto-drop silently drops a ticket whose findings are still live on
  an absolute-vs-relative path mismatch
state: in-progress
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