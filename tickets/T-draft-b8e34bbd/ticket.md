---
id: T-draft-b8e34bbd
title: 'vet fingerprint scan: self-exclusion regression matches its own catalog file'
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
