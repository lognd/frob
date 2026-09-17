---
id: T-draft-0b42af92
title: 'config.py residue left by T-4535: ARCH103, COV002 and SEC110 on src/frob/app/config.py
  (FROB_ROOT read), deferred behind T-3613''s lease'
state: queued
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
designated_repro_test: null
acceptance:
- text: GIVEN frob check --only gates --files src/frob/app/config.py src/frob/__main__.py
    WHEN run on dev THEN ARCH103, COV002 and SEC110 report zero errors for those files
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4535 fixed the hook-side residue but scoped out src/frob/app/config.py because T-3613 held its lease; T-3613 landed at 42bbe4c2b. Remaining: SEC110 on the FROB_ROOT environment read in _pyproject_file_for_args (add a frob:waive SEC110 with the reason that FROB_ROOT is a path, never a secret, matching the FROB_AGENT precedent), COV002 on the changed symbols (bind frob:tests to tests/unit/test_app_config_pyproject_root_t_draft_1f1ae69b.py nodes), ARCH103 per its remedy text. No behaviour change.