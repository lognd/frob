---
id: T-2521
title: 'auto-drop treats an incomplete measurement as proof of absence: 7 tickets
  dropped with ~66 live findings'
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/verify/
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_ticket_runner_gate_findings.py
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: 'Root-cause investigation (evidence in Done report) traced the actual

    auto-drop defect to two files outside the originally-declared

    src/frob/verify/ scope: _parse_error_findings_from_json/

    _collect_error_findings in app/ticket_runner/_verify.py (the identity

    extraction that silently drops a failed-but-diagnostic-less ToolResult

    as if it were a clean zero), and the auto-drop decision/reason text in

    app/ticket_runner/_rapid_sweep.py (T-1983''s own _maybe_drop_resolved_

    ticket / _close_resolved_sweep_tickets). Both must change together for

    the required behaviour (refuse-on-incomplete, reason states

    completeness); the mechanism does not live under src/frob/verify/ at

    all despite the ticket''s filed scope naming it.

    '
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: 'Root-cause investigation (evidence in Done report) traced the actual

    auto-drop defect to two files outside the originally-declared

    src/frob/verify/ scope: _parse_error_findings_from_json/

    _collect_error_findings in app/ticket_runner/_verify.py (the identity

    extraction that silently drops a failed-but-diagnostic-less ToolResult

    as if it were a clean zero), and the auto-drop decision/reason text in

    app/ticket_runner/_rapid_sweep.py (T-1983''s own _maybe_drop_resolved_

    ticket / _close_resolved_sweep_tickets). Both must change together for

    the required behaviour (refuse-on-incomplete, reason states

    completeness); the mechanism does not live under src/frob/verify/ at

    all despite the ticket''s filed scope naming it.

    '
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_ticket_runner_gate_findings.py
  reason: 'Root-cause investigation (evidence in Done report) traced the actual

    auto-drop defect to two files outside the originally-declared

    src/frob/verify/ scope: _parse_error_findings_from_json/

    _collect_error_findings in app/ticket_runner/_verify.py (the identity

    extraction that silently drops a failed-but-diagnostic-less ToolResult

    as if it were a clean zero), and the auto-drop decision/reason text in

    app/ticket_runner/_rapid_sweep.py (T-1983''s own _maybe_drop_resolved_

    ticket / _close_resolved_sweep_tickets). Both must change together for

    the required behaviour (refuse-on-incomplete, reason states

    completeness); the mechanism does not live under src/frob/verify/ at

    all despite the ticket''s filed scope naming it.

    '
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: 'Root-cause investigation (evidence in Done report) traced the actual

    auto-drop defect to two files outside the originally-declared

    src/frob/verify/ scope: _parse_error_findings_from_json/

    _collect_error_findings in app/ticket_runner/_verify.py (the identity

    extraction that silently drops a failed-but-diagnostic-less ToolResult

    as if it were a clean zero), and the auto-drop decision/reason text in

    app/ticket_runner/_rapid_sweep.py (T-1983''s own _maybe_drop_resolved_

    ticket / _close_resolved_sweep_tickets). Both must change together for

    the required behaviour (refuse-on-incomplete, reason states

    completeness); the mechanism does not live under src/frob/verify/ at

    all despite the ticket''s filed scope naming it.

    '
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_failed_silent_tool_result_yields_none_not_a_partial_set
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_failed_but_loud_tool_result_does_not_block_measurement
- tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_absolute_recorded_identity_matches_relative_vanished_entry
- tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_drops_a_fully_resolved_sweep_ticket
- tests/unit/test_rapid_sweep.py::TestIdentitiesStillReproducing::test_failed_silent_tool_result_is_unmeasurable_not_zero
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-18 against a full unbudgeted `frob check` on main.

SEVEN post-land sweep tickets were auto-dropped by T-1983's auto-drop
today. EVERY ONE of them names findings that are STILL LIVE right now:

    T-2506:  62 identities, 50 STILL LIVE
    T-2512:   6 identities,  4 STILL LIVE
    T-2513:   6 identities,  4 STILL LIVE
    T-2514:   6 identities,  4 STILL LIVE
    T-2515:   6 identities,  4 STILL LIVE
    T-2516:   4 identities,  2 STILL LIVE
    T-2518:   4 identities,  2 STILL LIVE

Concrete proof: T-2515's drop reason states "every (rule, file) identity
this ticket named (E501 src/frob/testing/_collect_kotlin.py, F811
tests/unit/test_app_runners_json_guard_t2492.py) is absent from the fresh
unscoped measurement ... i.e. no longer reproduces."

Both are present at this moment:
    E501 src/frob/testing/_collect_kotlin.py:65
    E501 src/frob/testing/_collect_kotlin.py:121
    F811 tests/unit/test_app_runners_json_guard_t2492.py (x6)

A DROP IS TERMINAL IN THIS REPO. There is no undrop. Roughly 66 live
finding identities were silently discarded today, and the only reason
this was caught is that a coordinator floor measurement happened to run
before the evidence aged out.

ROOT CAUSE, stated by the sweep tickets' own bodies:

    "The true per-finding count could not be independently re-measured
     this run (spawn refused/timeout/unparsable) -- re-run `frob check`
     unscoped against the file(s) below for the exact count before
     treating this identity count as a completeness claim."

The sweep KNEW its measurement was incomplete, said so in the ticket
body, and auto-drop then treated that unmeasured result as PROVEN ABSENT.
This is the purest possible instance of the T-2391 thesis: NOT_MEASURED
must never collapse into NOT_PRESENT. A drop is the most destructive
action in the system and it is currently keyed on the one signal that
cannot distinguish "I looked and it is gone" from "I could not look".

A SECOND CONTRIBUTING SHAPE, worth checking but NOT assumed: the recorded
identities carry ABSOLUTE paths
(`/home/logan/projects/frob/src/frob/testing/_collect_kotlin.py`) while a
fresh measurement reports repo-relative paths. This repo has already been
bitten by absolute-vs-relative identity matching (T-2314 voided 116
frob:waive directives the same way). If the comparison normalizes on one
side only, every identity would read as vanished regardless of
measurement completeness -- which would explain a 100% drop rate across
seven independent tickets better than intermittent spawn failure does.
DETERMINE WHICH of these two causes is operative before fixing; they need
different fixes and the evidence so far is consistent with both.

REQUIRED BEHAVIOUR:
1. Auto-drop must REFUSE to drop on any measurement that did not
   complete. Unmeasured => leave the ticket open, annotate why. Failing
   closed here costs a stale ticket; failing open destroys real findings
   permanently.
2. The drop reason must state the measurement's own completeness, not
   merely assert absence. "absent from a measurement that covered 15 of
   52 gates" is a different claim from "absent".
3. Identity comparison must normalize path shape on BOTH sides, with a
   positive control proving an absolute-vs-relative pair matches.

POSITIVE CONTROLS, BOTH DIRECTIONS, MANDATORY:
- a ticket whose findings genuinely vanished must still auto-drop
  (otherwise this fix just disables a useful mechanism);
- a ticket whose findings are live must NOT drop when the re-measurement
  is truncated, refused, or unparsable;
- an identity recorded absolute must match the same finding measured
  relative.

IMMEDIATE REMEDIATION, separate from the fix: the ~66 live identities
from the seven dropped tickets need to be re-filed, since drops are
terminal. Most are already visible in the current floor (74 errors) so
they are not lost to the project, but nothing tracks them as owned work
any more.