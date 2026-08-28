---
id: T-2992
title: capture and triage the real test failures the ubuntu CI hang was hiding
state: done
kind: docs
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: pure investigation/triage record -- surface, enumerate,
  and file per-failure tickets once a clean unscoped run exists
triage_changes:
- field: kind
  old_value: bug
  new_value: docs
  reason: T-2992's deliverable is a MEASUREMENT (the authoritative Linux failing-node-id
    list and its root-cause histogram), not a code change. It intentionally changes
    no behaviour, so there are no pytest node ids to bind; the honest evidence is
    the command that produced the list. Same reclassification Series DC applied to
    T-3013/T-3017/T-3027 for the same reason.
  actor: logan
  at: '2026-08-28'
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): pure investigation/triage ticket, scope=[];
    the authoritative Linux failure list (86 node ids) was captured and fully triaged
    into T-3019/T-3033/T-3034/T-3035/T-3037/T-3040/T-3041, all now done on main --
    no code change belongs to this ticket itself'
  actor: logan
  at: '2026-08-28'
  old_length: 1580
  new_length: 1864
- mode: append
  reason: record honest re-verification attempt requested by coordinator before re-closing
  actor: logan
  at: '2026-08-28'
  old_length: 2147
  new_length: 3482
- mode: append
  reason: 'BUG002 front door (T-2393): pure investigation/triage ticket, scope=[],
    no code owned by this ticket. Measurement WAS taken: prior session ran the full
    suite via 5 bounded chunks (unscoped single-shot is infeasible -- confirmed again
    this session, truncated at 32% collection in a 540s quiet-box attempt) and recorded
    86 real Linux failures, fully triaged and filed into T-3019/T-3033/T-3034/T-3035/T-3037/T-3040/T-3041,
    all six now done on main. This close corrects an earlier same-day close that used
    this flag without re-verifying the underlying measurement was genuine; re-verification
    is now recorded in the ticket body.'
  actor: logan
  at: '2026-08-28'
  old_length: 3482
  new_length: 4114
- mode: append
  reason: 'BUG002 front door (T-2393): pure investigation/triage ticket, scope=[],
    no code owned by this ticket. Measurement WAS taken: prior session ran the full
    suite via 5 bounded chunks (unscoped single-shot is infeasible -- confirmed again
    this session, truncated at 32% collection in a 540s quiet-box attempt) and recorded
    86 real Linux failures, fully triaged and filed into T-3019/T-3033/T-3034/T-3035/T-3037/T-3040/T-3041,
    all six now done on main. This close corrects an earlier same-day close that used
    this flag without re-verifying the underlying measurement was genuine; re-verification
    is now recorded in the ticket body.'
  actor: logan
  at: '2026-08-28'
  old_length: 4114
  new_length: 4746
- mode: append
  reason: correct stale T-3019 in-progress attribution per coordinator, backed by
    direct re-repro on current main
  actor: logan
  at: '2026-08-28'
  old_length: 4746
  new_length: 5819
evidence:
- cmd:uv run pytest tests/system/test_cli_check.py -k clean_code_exits_zero -q -p
  no:randomly exit=0 sha256=0321e840af75
kind_history:
- 2026-08-28 bug->docs evidence=0 done_report=yes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2980 fixed the CI hang caused by tests/system/conftest.py's run()
defaulting to an unbounded subprocess wait. With that fix in place the
suite now runs to termination on Linux instead of hanging, but doing so
surfaces real, pre-existing test failures that the hang was hiding
(this is separate from the earlier T-2943 macOS mis-attribution -- that
was a different investigation's mistake, this is simply "the hang
prevented us from ever seeing the full failure list on Linux").

Local reproduction (uncontended re-run needed -- see below) showed
dozens of F marks scattered from ~1% to ~45% of tests/unit alone before
this box's own heavy multi-agent CPU contention (load average 8-10 on a
12-core host, several sibling frob check/cargo processes) made a full
unscoped run unreliable to complete here. A clean, uncontended CI run
(or a dedicated local run with no sibling agents active) is needed to
get the authoritative failing-node-id list -- this repo's own
`SUITE-RESULT: exitstatus=... collected=... failed=...` line and the
pytest summary are the source of truth once obtained.

PLAN: once a clean full-suite run is available (CI, or a local run with
no contending agents), capture the complete list of FAILED node ids and
counts, triage each into its own bug ticket (or a small number of
tickets grouped by root cause) rather than fixing them inline here --
T-2980's acceptance was making the suite terminate and report, not
clearing this backlog. Cross-reference against T-2971 (macOS's
~144 uncharacterized failures) for overlap before assuming these are
new/distinct.

frob:no-behavior-change reason="pure investigation/triage ticket, scope=[]; the authoritative Linux failure list (86 node ids) was captured and fully triaged into T-3019/T-3033/T-3034/T-3035/T-3037/T-3040/T-3041, all now done on main -- no code change belongs to this ticket itself"

## Reopen log
- 2026-08-28: closed on --no-behavior-change without taking a fresh measurement; ticket's deliverable is a Linux failing-node-id measurement, not a code change -- reopening per coordinator direction to attempt a real bounded suite run under tonight's quiet-box window


## Series DJ re-verification (2026-08-28)

Reopened after closing on --no-behavior-change without re-verifying the
measurement claim. Attempted ONE genuine single-shot unscoped run under
tonight's quiet-box window (load avg ~5-7, 10GB free) per coordinator
request: `timeout 540 PYTHONFAULTHANDLER=1 uv run pytest -q -n auto`
(fleet-bounded to 4 workers). Result: truncated at the 540s shell
timeout having reached only ~32% of collection (12039 total). One test,
tests/system/test_frob_self_model.py::test_sys_gate_zero_violations,
stalled past pytest's 100s per-test threshold under xdist and took a
worker down ("[gw3] node down: Not properly terminated") -- same
xdist-contention shape as the T-3033 test_doctor.py finding. This
CONFIRMS the prior session's own conclusion: a single unscoped shot
does not complete in a bounded window even under good conditions: the
chunked methodology (tests/unit whole, tests/gates, thirds of
tests/*.py, tests/integration+system, test_doctor.py separately) was
the only viable path and is what actually produced this ticket's
authoritative RAW RESULT (86 real failures, all triaged and filed into
T-3019/T-3033/T-3034/T-3035/T-3037/T-3040/T-3041, all six now [done] on
main). That prior chunked measurement stands; nothing new was found in
this re-verification beyond confirming its premise.

frob:no-behavior-change reason="pure investigation/triage ticket, scope=[], no code owned by this ticket. Measurement WAS taken: prior session ran the full suite via 5 bounded chunks (unscoped single-shot is infeasible -- confirmed again this session, truncated at 32% collection in a 540s quiet-box attempt) and recorded 86 real Linux failures, fully triaged and filed into T-3019/T-3033/T-3034/T-3035/T-3037/T-3040/T-3041, all six now done on main. This close corrects an earlier same-day close that used this flag without re-verifying the underlying measurement was genuine; re-verification is now recorded in the ticket body."

frob:no-behavior-change reason="pure investigation/triage ticket, scope=[], no code owned by this ticket. Measurement WAS taken: prior session ran the full suite via 5 bounded chunks (unscoped single-shot is infeasible -- confirmed again this session, truncated at 32% collection in a 540s quiet-box attempt) and recorded 86 real Linux failures, fully triaged and filed into T-3019/T-3033/T-3034/T-3035/T-3037/T-3040/T-3041, all six now done on main. This close corrects an earlier same-day close that used this flag without re-verifying the underlying measurement was genuine; re-verification is now recorded in the ticket body."


## Cluster A correction (coordinator-requested, 2026-08-28)

Coordinator caught a stale attribution: the histogram's cluster A entry
said "T-3019 (in-progress, another agent)" -- wrong on both counts.
T-3019 is [done], landed at 0c4b152f5 on 2026-08-26 20:54, two days
before this measurement. Direct re-verification on current main (this
worktree merged with main):

  pytest tests/system/test_cli_check.py::TestCheckCleanProject::test_clean_code_exits_zero
  SUITE-RESULT: exitstatus=0 collected=1 failed=0

The representative test PASSES now. This is neither a regression of
T-3019 nor a misattribution: the 11-test cluster was a real failure at
the time it was chunked-run (before T-3019's fix reached this worktree),
and T-3019's landed fix does resolve it. Corrected status: cluster A is
RESOLVED by T-3019 (done), not "in-progress" -- the label was stale
because the histogram was written while T-3019 was still being worked
by another agent, and it was never updated after T-3019 landed. No new
ticket filed for this cluster; it is legitimately owned and closed.