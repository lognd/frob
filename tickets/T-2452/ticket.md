---
id: T-2452
title: _dispatch exceeds ARCH001 line threshold (found while T-2443 touched it)
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/__main__.py
evidence_scope:
- tests/unit/test_main_entry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: T-2452 is a pure ARCH001 line-count refactor with no behavior change; BUG002's
    designated evidence correctly passes at both parent and fix
  actor: logan
  at: '2026-08-18'
  old_length: 5117
  new_length: 5681
evidence:
- tests/unit/test_main_entry.py::TestRefactorDispatch::test_refactor_subcommand_dispatches_to_run_refactor_command
- tests/unit/test_main_entry.py::TestMainSigint::test_normal_dispatch_is_unaffected
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 80cae8861fbe747e299de57b4bf77533c79da3ce
---
`src/frob/__main__.py::_dispatch` is already at 81 lines on `main` --
over ARCH001's 60-line threshold (T-2443 discovered this while adding
one small `if argv[0] == "check": ...` branch, which the gate then
attributed to that diff even though the function was already over
threshold beforehand). Split the argv-routing special-cases (bind,
agent, worktree, sync-skills, release publish, refactor) out of
`_dispatch` into smaller per-verb dispatch helpers so the function
itself drops back under 60 lines, mirroring the existing
`_is_quality_bind`/`_is_release_publish` extraction pattern already used
for two of these special cases.