---
id: T-5476
title: 'vet fingerprint scan: self-exclusion regression matches its own catalog file'
state: done
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5476
branch: t-5476
scope:
- src/frob/vet/_capability_scan.py
- tests/vet_suite/test_fingerprint.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_capability_scan.py
  reason: 'fingerprint self-exclusion list is stale: src/frob/webapp/_websec_deser.py
    (a new WEBSEC109-116 sink detector, T-5309) contains yaml.load/eval/exec detection-pattern
    literals in its own docstrings/data that self-match FP-DESERIALIZE-YAML-001 etc,
    same self-match class as the already-excluded _cve_fingerprint.py/_dangerous_ops_*.py'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/vet_suite/test_fingerprint.py
  reason: 'fingerprint self-exclusion list is stale: src/frob/webapp/_websec_deser.py
    (a new WEBSEC109-116 sink detector, T-5309) contains yaml.load/eval/exec detection-pattern
    literals in its own docstrings/data that self-match FP-DESERIALIZE-YAML-001 etc,
    same self-match class as the already-excluded _cve_fingerprint.py/_dangerous_ops_*.py'
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
evidence:
- tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_scan_directory_fingerprints_excludes_the_catalog_itself
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing:
tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_scan_directory_fingerprints_excludes_the_catalog_itself

The vet fingerprint directory scanner now matches its OWN fingerprint
catalog file with rule FP-DESERIALIZE-YAML-001, where this test asserts
it must not (self-exclusion regression -- the scanner is supposed to skip
the catalog file it reads its own fingerprints from).

Fix: restore/extend the self-exclusion glob/path-check in the scan-
directory implementation under test so the catalog file is excluded
again. In touch-scope (tests/vet_suite/test_fingerprint.py and its
production symbol are not webapp/sql/strata-core).