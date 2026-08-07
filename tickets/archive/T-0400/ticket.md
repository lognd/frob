---
id: T-0400
title: 'AUDIT: vet real source resolution + fail-closed + registry completeness (docs/audits/vet.md)'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: T-0397
tier: ticket
sprint: null
scope:
- src/frob/vet/
- tests/test_vet*.py
- docs/modules/vet.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_vet*.py
  reason: 'audit fixes need tests/docs updated alongside src/frob/vet/, per dispatch
    scope: src/frob/vet/** plus its tests/docs'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/modules/vet.md
  reason: 'audit fixes need tests/docs updated alongside src/frob/vet/, per dispatch
    scope: src/frob/vet/** plus its tests/docs'
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_vet.py::TestCapabilityScan::test_c_source_fs_write_detected
- tests/test_vet.py::TestCapabilityScan::test_c_source_raw_fd_read_detected
- tests/test_vet.py::TestCapabilityScan::test_c_source_windows_exec_detected
- tests/test_vet.py::TestCapabilityScan::test_c_source_net_recv_detected
- tests/test_vet.py::TestFingerprintScan::test_whitespace_reformatted_needle_still_matches
- tests/test_vet.py::TestFingerprintScan::test_whitespace_tolerant_match_still_respects_comment_spans
- tests/test_vet.py::TestScanTreeSourceUnavailableFailClosed::test_missing_source_surfaces_error_violation
- tests/test_vet.py::TestScanTreeSourceUnavailableFailClosed::test_enforced_missing_source_fails_the_gate
- tests/test_vet.py::TestScanTreeMultipleLockfiles::test_scan_tree_scans_every_lockfile
- tests/test_vet.py::TestLockfileParsers::test_find_all_lockfiles_polyglot_repo
- tests/test_vet.py::TestLockfileParsers::test_find_all_lockfiles_single
- tests/test_vet.py::TestLockfileParsers::test_find_all_lockfiles_none
- tests/test_vet.py::TestLockfileParsers::test_find_all_lockfiles_direct_path
- tests/test_vet.py::TestObfuscationEnsemble::test_bidi_override_detected_in_c_file
- tests/test_vet.py::TestObfuscationEnsemble::test_bidi_override_detected_in_kotlin_file
- tests/test_vet.py::TestObfuscationEnsemble::test_split_string_payload_still_not_detected
designated_repro_test: null
threat: null
component: null
---
See docs/audits/vet.md. HIGH: source-unavailable dependency silently APPROVED (vet approves code it never read); only first lockfile scanned; CVE fingerprints + all non-Python needles rename/whitespace-evadable; C/C++ table misses file I/O + most exec/net; obfuscation entropy blind to triple-quoted/template/split strings and to C/C++/Kotlin. RIGHT-WAY fix: fail-CLOSED on unread source; scan ALL lockfiles; extend binding-aware resolution to TS/Rust/C/C++ + CVE fingerprints (ties to T-0377..0380); complete the per-language dangerous-surface tables; run obfuscation/bidi on all langs. Then re-audit until empty. MED/LOW in the doc.