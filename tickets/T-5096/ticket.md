---
id: T-5096
title: Restore --skip flag parity between frob ops natives and its flat twin
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: T-4806
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_ops.py
- src/frob/_cli_parsers/_misc.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: test_every_ops_leaf_matches_its_flat_twin[natives] passes
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35476139324 on dev: tests/unit/test_cli_group_parity.py TestOpsGroupParity test_every_ops_leaf_matches_its_flat_twin[natives] fails -- split out of T-4953 (which fixed the sibling frob quality check / frob check drift) once it became clear this is a different pair of files (src/frob/_cli_parsers/_ops.py's frob ops natives group leaf vs its flat top-level twin, likely built in src/frob/_cli_parsers/_misc.py) with the same class of drift: the grouped leaf's parser builder is missing an arg-registration helper call its flat twin makes. Investigate which helper is missing (same shape as T-4953's _add_check_skip_unified_arg fix) and add it to the natives group builder. NOTE: both files are currently leased by in-progress T-4731 -- this ticket cannot start until that lease clears; block on it.