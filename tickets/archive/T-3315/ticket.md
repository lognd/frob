---
id: T-3315
title: frob ticket sweep refuses on a done ticket with no stated remedy after a post-close
  scope fix
state: done
kind: bug
origin: human
created: '2026-08-28'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/ticket_runner/_lifecycle.py
- tests/unit/test_ticket_sweep_terminal_state.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: sweep command handler (_sweep_cmd) actually lives here, not _verify.py --
    correcting the ticket's declared scope to match reality
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_ticket_sweep_terminal_state.py
  reason: MUST-FIRE/MUST-STAY-QUIET regression tests for sweep on terminal states
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/modules/gates.md
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/test_ticket_lifecycle.py
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/test_ticket_runner_pytest_env.py
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/test_tickets.py
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/test_tickets_evidence_cli.py
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/test_tickets_no_scope.py
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/ticket_land_suite/test_claim_close.py
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_pytest_spawn_env_wiring.py
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_ticket_runner_designate_repro.py
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_ticket_runner_gate_findings.py
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_ticket_runner_land_release.py
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_ticket_runner_ledger_mirror.py
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_ticket_runner_repro_merge_base.py
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_ticket_runner_venv_sync_t3320.py
  reason: 'SCOPE002 closure: _lifecycle.py''s existing frob:doc/frob:tests edges (pre-existing,
    unrelated to the sweep fix itself) require these in scope to close the declaration-time
    triple'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: docs/modules/gates.md
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: docs/modules/tickets-data-storage.md
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: docs/modules/tickets-landing.md
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: docs/modules/tickets-lifecycle.md
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/test_ticket_lifecycle.py
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/test_ticket_runner_pytest_env.py
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/test_ticket_work_and_land_finish.py
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/test_tickets.py
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/test_tickets_evidence_cli.py
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/test_tickets_no_scope.py
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/ticket_land_suite/test_claim_close.py
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/unit/test_app_runners_batch7.py
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/unit/test_pytest_spawn_env_wiring.py
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/unit/test_ticket_runner_designate_repro.py
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/unit/test_ticket_runner_gate_findings.py
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/unit/test_ticket_runner_land_release.py
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/unit/test_ticket_runner_ledger_mirror.py
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/unit/test_ticket_runner_repro_merge_base.py
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/unit/test_ticket_runner_venv_sync_t3320.py
  reason: 'revert: docs/modules/gates.md alone pulled in 3143 more closure warnings
    (a massive shared design doc, unrelated to this one-function sweep fix) -- widening
    scope this far is disproportionate; filing the SCOPE002/gates.md closure-explosion
    problem as its own out-of-scope ticket instead'
  actor: logan
  at: '2026-09-05'
evidence:
- tests/unit/test_ticket_sweep_terminal_state.py::TestSweepOnTerminalState::test_sweep_on_done_ticket_is_a_quiet_success
- tests/unit/test_ticket_sweep_terminal_state.py::TestSweepOnTerminalState::test_sweep_on_dropped_ticket_is_a_quiet_success
- tests/unit/test_ticket_sweep_terminal_state.py::TestSweepOnTerminalState::test_sweep_on_queued_ticket_still_refuses
- tests/unit/test_ticket_sweep_terminal_state.py::TestSweepOnTerminalState::test_sweep_on_in_progress_ticket_still_runs
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-036).

`frob ticket scope T-0015 --add ...` succeeds on an already-DONE ticket (a
legitimate post-close scope correction, e.g. tidying the record), but the
follow-up `frob ticket sweep T-0015` -- which the CLI's own remediation text
recommends after a scope change -- then exits 1 (FAST_EXIT1) because the
ticket is closed. The scope edit itself took effect and cleared SCOPE001, so
the sweep refusal is a dead end with no stated remedy: the fix already
worked, but the tool tells you to run a command that cannot succeed.

WHAT TO BUILD: either (a) `sweep` should be a genuine no-op success (exit 0,
"nothing to sweep, ticket is closed") on a done/dropped ticket rather than a
FAST_EXIT1 refusal, since a closed ticket has no more pre-work sweep to
perform and that is a legitimate, expected state -- not a failure; or (b) if
sweep must stay closed-refusing for a real reason, whatever remediation text
led the user to run it post-close in the first place should stop suggesting
it. Confirm which call site prints that suggestion before picking (a) or (b).

MUST-FIRE / MUST-STAY-QUIET: `frob ticket sweep <id>` on an in-progress
ticket behaves exactly as today; on a done/dropped ticket it either succeeds
quietly (0) or the remediation text that recommends it stops appearing for
already-closed tickets -- no more dead-end recommendation.