---
id: T-1684
title: 'rapid: post-land sweep runs detached, files a ticket on red instead of blocking
  the land'
state: done
kind: feature
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/_cli_parsers/_ticket/_closeout.py
- tests/unit/test_rapid_sweep.py
- docs/modules/tickets.md
- tests/test_ticket_work_and_land_finish.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/_cli_parsers/_ticket/__init__.py
- design/frob.strata
- docs/modules/app.md
- docs/guides/agentic-workflow.md
- src/frob/gates/_wire.py
- src/frob/tickets/_profile.py
- src/frob/tickets/_evidence.py
- docs/strata/roadmap.md
- tests/unit/test_rapid_debt.py
- tests/unit/test_profile.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: 'SCOPE002 closure: the doc anchors for both the new deferred sweep and the
    existing _land_cmd sweep family live in docs/modules/tickets.md; the existing
    sweep tests live in tests/test_ticket_work_and_land_finish.py; _unscoped_error_findings
    (reused by the deferred sweep) calls private helpers in _verify.py; and the new
    sweep-async CLI verb needs its AppConfig field, external-config passthrough, and
    parser registration'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: 'SCOPE002 closure: the doc anchors for both the new deferred sweep and the
    existing _land_cmd sweep family live in docs/modules/tickets.md; the existing
    sweep tests live in tests/test_ticket_work_and_land_finish.py; _unscoped_error_findings
    (reused by the deferred sweep) calls private helpers in _verify.py; and the new
    sweep-async CLI verb needs its AppConfig field, external-config passthrough, and
    parser registration'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: 'SCOPE002 closure: the doc anchors for both the new deferred sweep and the
    existing _land_cmd sweep family live in docs/modules/tickets.md; the existing
    sweep tests live in tests/test_ticket_work_and_land_finish.py; _unscoped_error_findings
    (reused by the deferred sweep) calls private helpers in _verify.py; and the new
    sweep-async CLI verb needs its AppConfig field, external-config passthrough, and
    parser registration'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/app/config.py
  reason: 'SCOPE002 closure: the doc anchors for both the new deferred sweep and the
    existing _land_cmd sweep family live in docs/modules/tickets.md; the existing
    sweep tests live in tests/test_ticket_work_and_land_finish.py; _unscoped_error_findings
    (reused by the deferred sweep) calls private helpers in _verify.py; and the new
    sweep-async CLI verb needs its AppConfig field, external-config passthrough, and
    parser registration'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'SCOPE002 closure: the doc anchors for both the new deferred sweep and the
    existing _land_cmd sweep family live in docs/modules/tickets.md; the existing
    sweep tests live in tests/test_ticket_work_and_land_finish.py; _unscoped_error_findings
    (reused by the deferred sweep) calls private helpers in _verify.py; and the new
    sweep-async CLI verb needs its AppConfig field, external-config passthrough, and
    parser registration'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/_cli_parsers/_ticket/__init__.py
  reason: 'SCOPE002 closure: the doc anchors for both the new deferred sweep and the
    existing _land_cmd sweep family live in docs/modules/tickets.md; the existing
    sweep tests live in tests/test_ticket_work_and_land_finish.py; _unscoped_error_findings
    (reused by the deferred sweep) calls private helpers in _verify.py; and the new
    sweep-async CLI verb needs its AppConfig field, external-config passthrough, and
    parser registration'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: design/frob.strata
  reason: design/frob.strata carries the SYS100 capability declarations for the new
    module plus the SYS104 interface= rows (written by frob sys sync-interface); app.md
    and agentic-workflow.md are the doc anchors of the AppConfig/parser symbols this
    ticket touches; _wire.py is the ROOT-CAUSE fix for WIRE001 firing on every dict-table-dispatched
    CLI handler -- the new sweep-async handler is wired exactly like every other frob
    ticket verb, and waiving that would have taught the gate's own false-positive
    class instead of fixing it
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/app.md
  reason: design/frob.strata carries the SYS100 capability declarations for the new
    module plus the SYS104 interface= rows (written by frob sys sync-interface); app.md
    and agentic-workflow.md are the doc anchors of the AppConfig/parser symbols this
    ticket touches; _wire.py is the ROOT-CAUSE fix for WIRE001 firing on every dict-table-dispatched
    CLI handler -- the new sweep-async handler is wired exactly like every other frob
    ticket verb, and waiving that would have taught the gate's own false-positive
    class instead of fixing it
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/guides/agentic-workflow.md
  reason: design/frob.strata carries the SYS100 capability declarations for the new
    module plus the SYS104 interface= rows (written by frob sys sync-interface); app.md
    and agentic-workflow.md are the doc anchors of the AppConfig/parser symbols this
    ticket touches; _wire.py is the ROOT-CAUSE fix for WIRE001 firing on every dict-table-dispatched
    CLI handler -- the new sweep-async handler is wired exactly like every other frob
    ticket verb, and waiving that would have taught the gate's own false-positive
    class instead of fixing it
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/gates/_wire.py
  reason: design/frob.strata carries the SYS100 capability declarations for the new
    module plus the SYS104 interface= rows (written by frob sys sync-interface); app.md
    and agentic-workflow.md are the doc anchors of the AppConfig/parser symbols this
    ticket touches; _wire.py is the ROOT-CAUSE fix for WIRE001 firing on every dict-table-dispatched
    CLI handler -- the new sweep-async handler is wired exactly like every other frob
    ticket verb, and waiving that would have taught the gate's own false-positive
    class instead of fixing it
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_profile.py
  reason: COV001 closure for the two T-1681 symbols this ticket's own rapid path calls
    (record_rapid_debt is the deferred sweep's debt sink; ratchet_override_enabled
    is what makes rapid reachable in this repo at all) -- both were public with no
    doc anchor, now anchored to the new tickets.md section
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: COV001 closure for the two T-1681 symbols this ticket's own rapid path calls
    (record_rapid_debt is the deferred sweep's debt sink; ratchet_override_enabled
    is what makes rapid reachable in this repo at all) -- both were public with no
    doc anchor, now anchored to the new tickets.md section
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/strata/roadmap.md
  reason: 'SCOPE002: pulling design/frob.strata into scope pulls in every node''s
    frob:doc target, which is the single self-hosting-commitments anchor in docs/strata/roadmap.md'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_rapid_debt.py
  reason: 'TEST001 closure: the two T-1681 symbols this ticket anchors also had no
    unit test; test_rapid_debt.py covers record_rapid_debt (and caught a real bug:
    run_argv reports spawn failure via Err, not nonzero exit, so a failed rev-parse
    recorded commit="" instead of "unknown"), test_profile.py gains TestRatchetOverride'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_profile.py
  reason: 'TEST001 closure: the two T-1681 symbols this ticket anchors also had no
    unit test; test_rapid_debt.py covers record_rapid_debt (and caught a real bug:
    run_argv reports spawn failure via Err, not nonzero exit, so a failed rev-parse
    recorded commit="" instead of "unknown"), test_profile.py gains TestRatchetOverride'
  actor: logan
  at: '2026-08-06'
body_changes:
- mode: append
  reason: 'T-4770: preserve concrete examples for the 4 by-reference wiring shapes
    trimmed from _wire.py'
  actor: logan
  at: '2026-09-19'
  old_length: 1002
  new_length: 1841
evidence:
- tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun::test_new_findings_file_a_ticket_and_rebaseline
- tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun::test_unmeasurable_check_leaves_the_baseline_untouched
- tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepSpawn::test_exec_disabled_records_debt_and_refuses
- tests/unit/test_rapid_debt.py::TestRecordRapidDebt::test_records_a_commit_field_even_outside_a_git_repo
- tests/unit/test_profile.py::TestRatchetOverride::test_explicit_true_overrides
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Under rapid, land waits ~5 minutes on a synchronous full-repo unscoped
frob check (plus the T-1463 baseline snapshot check, joined just before
it). That is the entire land latency; frob startup (0.24s) and graph
build (5.4s) are not. Target is <10s per land.

Change: under rapid only, skip the T-1463 baseline thread and replace the
synchronous post-land sweep with a detached child (`frob ticket
sweep-async`) that runs the same unscoped check against a ROLLING
baseline stored at `.frob/rapid-sweep-baseline.json` (the last recorded
absolute error set), files a bug ticket naming any new (rule, file)
pairs, and NEVER reverts an already-published commit. Each deferred sweep
appends a rapid-debt.jsonl line, so the unverified window is a
machine-readable record rather than a silent gap.

The rolling baseline is what makes this a single check: standard mode
pays two full checks (baseline + post), rapid pays zero in the
foreground and one in the background.

standard/fortress paths are untouched.


T-4770 follow-up (condensed from a comment above keyword_arg_pattern in
src/frob/gates/_wire.py, trimmed for DOCARCH002's 12-line cap): the
T-1684 example is "sweep-async": _sweep_async, in
_ticket_dispatch_table. The T-1807 module-qualified example is
"frob_map": _tools.frob_map, -- every row of _TOOL_DISPATCH in
src/frob/serve/_socketd.py uses this exact shape. The T-2778 example is
on_tick=_print_tick, scripts/wait_for_land_slot.py's own _print_tick
passed to wait_for_slot's on_tick= parameter -- none of the wrapper-
marker/job-table/dict-table alternatives name a fixed marker function,
a job-table constructor, or a dict literal; this is just an ordinary
call passing the symbol by name as one of its OTHER arguments. T-1831's
anchor is formatter_class=_GroupedHelpFormatter, whose own docstring
says "must never be closed".