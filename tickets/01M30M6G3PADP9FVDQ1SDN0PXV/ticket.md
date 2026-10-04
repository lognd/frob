+++
id = "01M30M6G3PADP9FVDQ1SDN0PXV"
title = "frob ops natives missing --path flag its flat twin frob natives has (CLI group parity)"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-21T00:00:00Z"
updated = "2026-09-21T00:00:02Z"
aliases = ["T-5238"]
scope = ["tests/unit/test_cli_group_parity.py"]

[[links]]
kind = "blocked-by"
target = "01M2VFD1JJD17QEF1ZFXA7C3R1"
+++

Found while burning down fresh CI run 35654510898, re-verified on current dev tip. tests/unit/test_cli_group_parity.py::TestOpsGroupParity::test_every_ops_leaf_matches_its_flat_twin[natives] fails: 'frob ops natives' vs 'frob natives' option strings differ -- the flat twin has {--help, --path, -h}, the grouped ops twin only has {--help, -h}. A --path flag was added to one CLI entry point's parser without mirroring it on the other. Fix: add --path to whichever parser is missing it (likely the ops-group subcommand wiring in src/frob/app/_cli_parsers/).

## Drop reason
- 2026-09-22: duplicate of T-5205 (ops natives --path parity) (absorbed by T-5205)
