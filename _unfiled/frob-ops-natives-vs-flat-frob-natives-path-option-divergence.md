+++
id = "01M30M6G4RT7S5626S209Y7065"
title = "frob ops natives vs flat frob natives: --path option divergence (test_cli_group_parity pre-existing failure)"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-21T00:00:00Z"
updated = "2026-09-21T00:00:02Z"
aliases = ["T-5272"]
scope = ["src/frob/_cli_parsers/_ops.py"]
+++

found while working T-4690: tests/unit/test_cli_group_parity.py::TestOpsGroupParity::test_every_ops_leaf_matches_its_flat_twin[natives] fails on dev (confirmed pre-existing, unrelated to T-4690 -- _ops.py's natives leaf was not touched by that ticket). 'frob ops natives' has only {-h,--help}; flat 'frob natives' additionally has --path. One of the two parsers is missing a flag the other has; needs investigation and a fix to restore parity.

## Drop reason
- 2026-09-22: duplicate of T-5205 (ops natives --path parity) (absorbed by T-5205)
