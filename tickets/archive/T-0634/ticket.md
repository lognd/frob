---
id: T-0634
title: 'fix circular import: frob.testing standalone import fails through frob.gates'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/**
- src/frob/gates/**
- tests/unit/testing/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/testing/**
  reason: regression test for the standalone-import cycle fix (T-0634)
  actor: logan
  at: '2026-07-26'
evidence:
- tests/unit/testing/test_import_cycle.py::test_frob_testing_imports_standalone_in_fresh_interpreter
designated_repro_test: null
acceptance:
- text: GIVEN a fresh python process WHEN import frob.testing runs as the first frob
    import THEN it succeeds and the test-file workaround import is removed
  evidence:
  - tests/unit/testing/test_import_cycle.py::test_frob_testing_imports_standalone_in_fresh_interpreter
threat: null
component: null
---
import frob.testing as the first frob-touching import raises ImportError (cannot import name CollectedTests) through the frob.gates cycle; masked in the full suite by import order, breaks standalone runs. tests/unit/testing/test_stability.py carries a documented workaround (import frob.gates first). Was T-draft-3d5f6965 in T-0575's worktree; the draft was dropped at land (see the auto-finalize field-failure ticket).