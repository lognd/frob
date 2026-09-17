---
id: T-4535
title: 'Post-land residue from T-4502 and T-3615: hook and config.py coverage, affect,
  ARCH103 and SEC110 findings'
state: done
kind: bug
origin: agent
created: '2026-09-16'
priority: medium
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/frob-timeout-guard.py
- .claude/hooks/frob-suggest.py
- src/frob/__main__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/config.py
  reason: collides with T-3613's in-progress lease on this file (a larger, unrelated
    land-queue feature ticket); deferring the ARCH103/COV002/SEC110 findings on config.py
    until T-3613 lands or coordinates -- reporting to coordinator
  actor: logan
  at: '2026-09-16'
body_changes:
- mode: append
  reason: 'BUG002 structurally untestable via pytest: gate/doc-metadata state, not
    application code'
  actor: logan
  at: '2026-09-16'
  old_length: 624
  new_length: 1824
evidence:
- tests/test_hook_frob_timeout_guard.py::test_ticket_work_under_min_timeout_is_blocked
- tests/test_hook_frob_suggest.py::test_second_identical_check_pipeline_is_allowed_through
- tests/unit/test_main_entry.py::TestMainSigint::test_normal_dispatch_is_unaffected
designated_repro_test: null
acceptance:
- text: GIVEN frob check --only gates --files on the four owned files WHEN run THEN
    AFFECT001/ARCH103/COV001/COV002/COV005/COV007/SEC110 report zero errors
  evidence:
  - tests/test_hook_frob_timeout_guard.py::test_ticket_work_under_min_timeout_is_blocked
  - tests/test_hook_frob_suggest.py::test_second_identical_check_pipeline_is_allowed_through
  - tests/unit/test_main_entry.py::TestMainSigint::test_normal_dispatch_is_unaffected
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Quarantine raised by the post-land sweep on batch (86576a646 T-4502, ddd4d80fa T-3615) 2026-09-16: AFFECT001/COV001/COV005/COV007 on .claude/hooks/frob-timeout-guard.py (the coordinator's ARCH001 split added _deny and _needs_large_timeout without doc/test edges); COV002 on .claude/hooks/frob-suggest.py; ARCH103, COV002 and SEC110 on src/frob/app/config.py (FROB_ROOT read in _pyproject_file_for_args: SEC110 wants a frob:waive noting FROB_ROOT is a path, not a secret); COV002 on src/frob/__main__.py. No behaviour change: bind frob:doc/frob:tests edges, add the SEC110 waiver with reason, fix ARCH103 per its remedy text.

frob:waive BUG002 reason="post-land sweep residue: the defect is frob check GATE state (COV001/COV005/COV007 on .claude/hooks/frob-timeout-guard.py after its ARCH001 split) with no application-behavior change a pytest repro can exercise at the parent commit. Fix is a frob:doc directive move (main gets it, the redundant one on the split-out _deny private helper is removed) -- the SEC110/ARCH103 findings on src/frob/app/config.py and the config.py-adjacent COV002 were scoped out of this ticket (collision with T-3613 in-progress lease on that file; reported to coordinator). COV002 on frob-suggest.py and src/frob/__main__.py resolved once measured with --ticket T-4535 --base dev (this ticket own scope covers both files). Repro is the frob check invocation: frob check --only coverage --only drift --only affect_drift --only clones --ticket T-4535 --base dev --files .claude/hooks/frob-timeout-guard.py --files .claude/hooks/frob-suggest.py --files src/frob/__main__.py --files docs/guides/claude-hooks.md reported 0 errors for these files both before and after this specific edit once measured correctly (the stale-base-vs-dev measurement trap already documented on T-draft-357dade2/T-4532)."