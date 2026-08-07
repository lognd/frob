---
id: T-0439
title: 'feat(sec-patterns): needle/fingerprint pattern-scan gate for CVE code-smell
  corpus (SEC-CVE-FINGERPRINT-*)'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/
- src/frob/gates/
- docs/design/registry/weaknesses.yaml
- tests/unit/strata/
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/strata/
  reason: T-0439 strata work maps to tests/unit/strata/
  actor: logan
  at: '2026-07-20'
evidence:
- tests/unit/strata/test_cve_fingerprint_scan.py::TestScanTextForFingerprints::test_smelly_text_fires
- tests/unit/strata/test_cve_fingerprint_scan.py::TestScanTextForFingerprints::test_clean_text_does_not_fire
- tests/unit/strata/test_cve_fingerprint_scan.py::TestGate::test_smelly_file_fires
designated_repro_test: null
threat: null
component: null
---
