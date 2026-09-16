---
id: T-draft-c3f8068d
title: 'Post-land residue from T-4502 and T-3615: hook and config.py coverage, affect,
  ARCH103 and SEC110 findings'
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
- .claude/hooks/frob-timeout-guard.py
- .claude/hooks/frob-suggest.py
- src/frob/app/config.py
- src/frob/__main__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN frob check --only gates --files on the four owned files WHEN run THEN
    AFFECT001/ARCH103/COV001/COV002/COV005/COV007/SEC110 report zero errors
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Quarantine raised by the post-land sweep on batch (86576a646 T-4502, ddd4d80fa T-3615) 2026-09-16: AFFECT001/COV001/COV005/COV007 on .claude/hooks/frob-timeout-guard.py (the coordinator's ARCH001 split added _deny and _needs_large_timeout without doc/test edges); COV002 on .claude/hooks/frob-suggest.py; ARCH103, COV002 and SEC110 on src/frob/app/config.py (FROB_ROOT read in _pyproject_file_for_args: SEC110 wants a frob:waive noting FROB_ROOT is a path, not a secret); COV002 on src/frob/__main__.py. No behaviour change: bind frob:doc/frob:tests edges, add the SEC110 waiver with reason, fix ARCH103 per its remedy text.