---
id: T-0877
title: 'frob scaffold pool CLI: wire warm/lease/status subcommands onto the T-0738
  pool API'
state: done
kind: feature
origin: agent
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/scaffold_runner.py
- src/frob/app/config.py
- src/frob/__main__.py
- Makefile
- docs/guides/worktree-pool.md
- tests/system/test_scaffold_pool_cli.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_scaffold_pool_cli.py::TestScaffoldPoolCli::test_warm_lease_status_roundtrip
- tests/system/test_scaffold_pool_cli.py::TestScaffoldPoolCli::test_lease_on_empty_pool_fails
designated_repro_test: null
acceptance:
- text: GIVEN a frob-enabled repo WHEN `uv run frob scaffold pool warm 2` then `pool
    status` then `pool lease` run THEN two worktrees are warmed, status lists them,
    and lease returns a merged-current worktree path with a background refill
  evidence:
  - tests/system/test_scaffold_pool_cli.py::TestScaffoldPoolCli::test_warm_lease_status_roundtrip
- text: GIVEN the Makefile pool targets WHEN they run THEN they delegate to the CLI
    subcommand, no inline python remains
  evidence:
  - tests/system/test_scaffold_pool_cli.py::TestScaffoldPoolCli::test_warm_lease_status_roundtrip
threat: null
component: scaffold
---
Follow-on to T-0738 (landed 0.139.0): the warm-pool API (warm_pool, lease_worktree, pool_status in frob.scaffold._pool) is reachable only through Makefile targets calling the Python API. Wire a real `frob scaffold pool` CLI subcommand group (warm N / lease / status) through app/scaffold_runner.py + app/config.py + __main__.py, replacing the Makefile's inline-python shims with thin CLI calls. Refiled from worktree draft T-0877 (refiled from a land-lost worktree draft) which did not survive T-0738's land (drafts-die-at-land hazard); T-0738's Done report references that draft id.