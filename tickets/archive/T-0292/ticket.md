---
id: T-0292
title: COV003 remediation hint references nonexistent 'frob test --collect' flag
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/invariants.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov003_remediation_hint_names_no_nonexistent_flag
designated_repro_test: null
acceptance:
- text: given a COV003 evidence-resolution failure, when the error message prints
    its remediation hint, then the suggested command is one that actually exists (frob
    test has no --collect flag today); either add the flag or change the hint to the
    real refresh path
  evidence: []
threat: null
component: null
---
Hit live 2026-07-19 while closing T-0282: COV003 says "run: frob test --collect to refresh" but `frob test` has no --collect option (argparse rejects it). Root cause of the false COV003 was a stale .frob/pytest-collect.json cache after a merge added new evidence tests; the cache did refresh on the next collection pass, but the user-facing hint points at a nonexistent flag. Fix: either implement `frob test --collect` (force a collection-cache rebuild without running tests) -- the cleaner option, since there is a genuine need to refresh the cache on demand -- or correct the hint to whatever the real refresh path is. Prefer adding the flag.