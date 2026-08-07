---
id: T-0725
title: 'strata: export golden fixtures (k8s/seccomp/iam) drifted from design/frob.strata
  after fleet flows landed'
state: done
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/strata/test_export_golden.py
- tests/golden/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/unit/strata/golden/**
  reason: 'Ticket scope named tests/unit/strata/golden/** but the actual committed

    golden fixtures for test_export_golden.py live at tests/golden/** (verified:

    tests/unit/strata/golden/ does not exist; tests/golden/frob_export_iam.json,

    frob_export_k8s.yaml, frob_export_seccomp.json do, and are exactly what

    test_export_golden.py reads via _GOLDEN_DIR = repo_root/tests/golden).

    Correcting the scope glob to the real path so regenerating these fixtures

    (the ticket''s whole point) is in-scope rather than a silent expansion.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/golden/**
  reason: 'Ticket scope named tests/unit/strata/golden/** but the actual committed

    golden fixtures for test_export_golden.py live at tests/golden/** (verified:

    tests/unit/strata/golden/ does not exist; tests/golden/frob_export_iam.json,

    frob_export_k8s.yaml, frob_export_seccomp.json do, and are exactly what

    test_export_golden.py reads via _GOLDEN_DIR = repo_root/tests/golden).

    Correcting the scope glob to the real path so regenerating these fixtures

    (the ticket''s whole point) is in-scope rather than a silent expansion.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_iam
designated_repro_test: null
threat: null
component: null
---
found while working T-0699: tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s/test_seccomp/test_iam fail on a clean worktree at main tip (e2f38a51, no T-0699 changes involved) -- design/frob.strata gained fleet node/flows (T-0614 era merge) but the committed golden JSON fixtures were not regenerated to match. Pre-existing, unrelated to T-0699's SYS2xx resource-contention work; regenerate the golden fixtures or fix whatever drifted.