---
id: T-0221
title: frob vet <lockfile> misparses path arg and exits 0 on ERROR
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- src/frob/app/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestLockfileParsers::test_find_lockfile_direct
- tests/test_vet.py::TestLockfileParsers::test_find_lockfile_bad_name
- tests/test_vet.py::TestScanTreeLockArg::test_scan_tree_lockfile_arg
- tests/test_vet.py::TestScanTreeLockArg::test_scan_tree_unsupp_err
- tests/test_vet.py::TestVetRunnerLockArg::test_run_lockfile_arg
- tests/test_vet.py::TestVetRunnerLockArg::test_run_unsupp_nonzero
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 3: frob vet uv.lock -> 'no supported lockfile under /repo/uv.lock' + ERROR LockfileUnsupported + EXIT 0. Two bugs: the path arg is treated as a directory root only (a lockfile path should be accepted), and the error exit code is lost (exit-0-on-error is gate-poisoning, same vacuous-pass doctrine as T-0184). Regression tests for both.