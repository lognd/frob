---
id: T-4953
title: Restore --skip flag parity between frob quality check and frob check
state: done
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
- src/frob/_cli_parsers/_quality.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_cli_group_parity.py::TestQualityGroupParity::test_every_quality_leaf_matches_its_flat_twin
designated_repro_test: null
acceptance:
- text: test_every_quality_leaf_matches_its_flat_twin[check] passes
  evidence:
  - tests/unit/test_cli_group_parity.py::TestQualityGroupParity::test_every_quality_leaf_matches_its_flat_twin
acceptance_amendments:
- op: remove
  index: 1
  old_text: test_every_ops_leaf_matches_its_flat_twin[natives] passes
  new_text: null
  reason: split out into T-5057 (Restore --skip flag parity between frob ops natives
    and its flat twin), which is BLOCKED on T-4731's live lease on src/frob/_cli_parsers/_ops.py
    and _misc.py -- this ticket's own scope (_quality.py only) cannot satisfy this
    criterion, and its evidence was previously mis-bound to a test that does not cover
    the natives path
  actor: logan
  at: '2026-09-19'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35476139324 on dev: tests/unit/test_cli_group_parity.py TestQualityGroupParity test_every_quality_leaf_matches_its_flat_twin[check] fails because frob quality check registers _add_check_skip_args but not _add_check_skip_unified_arg, unlike its flat twin frob check (src/frob/_cli_parsers/_check.py's top-level check_p registers both), so the grouped leaf is missing the unified --skip STAGE flag. Same root cause likely explains the [natives] ops parity failure -- investigate src/frob/_cli_parsers/_ops.py::natives vs src/frob/_cli_parsers/_misc.py::natives for the analogous drift and fix both leaves to call the same helper set as their flat twin.