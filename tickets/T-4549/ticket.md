---
id: T-4549
title: 'config.py residue left by T-4535: ARCH103, COV002 and SEC110 on src/frob/app/config.py
  (FROB_ROOT read), deferred behind T-3613''s lease'
state: dropped
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
- src/frob/app/config.py
- src/frob/__main__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 structurally untestable via pytest: gate/doc-metadata state, not
    application code'
  actor: logan
  at: '2026-09-16'
  old_length: 500
  new_length: 1374
evidence:
- tests/unit/test_app_config_pyproject_root_t_draft_1f1ae69b.py::TestPyprojectFileForArgs::test_explicit_ticket_path_wins_over_cwd
- tests/unit/test_app_config_pyproject_root_t_draft_1f1ae69b.py::TestPyprojectFileForArgs::test_frob_root_env_wins_over_cwd_when_no_explicit_path
designated_repro_test: null
acceptance:
- text: GIVEN frob check --only gates --files src/frob/app/config.py src/frob/__main__.py
    WHEN run on dev THEN ARCH103, COV002 and SEC110 report zero errors for those files
  evidence:
  - tests/unit/test_app_config_pyproject_root_t_draft_1f1ae69b.py::TestPyprojectFileForArgs::test_explicit_ticket_path_wins_over_cwd
  - tests/unit/test_app_config_pyproject_root_t_draft_1f1ae69b.py::TestPyprojectFileForArgs::test_frob_root_env_wins_over_cwd_when_no_explicit_path
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4535 fixed the hook-side residue but scoped out src/frob/app/config.py because T-3613 held its lease; T-3613 landed at 42bbe4c2b. Remaining: SEC110 on the FROB_ROOT environment read in _pyproject_file_for_args (add a frob:waive SEC110 with the reason that FROB_ROOT is a path, never a secret, matching the FROB_AGENT precedent), COV002 on the changed symbols (bind frob:tests to tests/unit/test_app_config_pyproject_root_t_draft_1f1ae69b.py nodes), ARCH103 per its remedy text. No behaviour change.

frob:waive BUG002 reason="post-land sweep residue: SEC110/COV002/ARCH103 on src/frob/app/config.py -- SEC110 fixed with a waiver directive (FROB_ROOT is a path marker, not a secret, same posture as FROB_AGENT/FROB_WORKTREE); COV002 was already satisfied by pre-existing frob:tests edges on _pyproject_file_for_args; ARCH103 does not fire on this file (frob check --only arch reports 0 errors/no ARCH103 hit here). None of this is application-behavior a pytest repro can exercise -- gate/doc-metadata state only. Repro is the frob check invocation: frob check --only coverage --only drift --only affect_drift --only clones --ticket T-4548 --base dev --files src/frob/app/config.py --files src/frob/__main__.py reports 0 errors for these files both before and after (the 5 remaining errors in the run are unrelated T-4531/T-4515 residue dev has not yet absorbed)."

## Drop reason
- 2026-09-18: resolved by T-4548 (config residue land): SEC110 waiver on FROB_ROOT read is on dev at src/frob/app/config.py, COV002 edges pre-existing, ARCH103 does not fire; acceptance already bound to the pyproject-root tests (absorbed by T-4548)
