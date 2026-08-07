---
id: T-0235
title: exhaustive log/print call-site classification across src/frob (T-0202 follow-up)
state: done
kind: ux
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestScanTreeLockArg::test_scan_tree_lockfile_arg
- tests/test_vet.py::TestScanTreeLockArg::test_scan_tree_unsupp_err
- tests/test_vet.py::TestScanTreeWithLocalSource::test_scan_tree_detects_capabilities_from_node_modules
- tests/test_vet.py::TestScanTreeWithLocalSource::test_scan_tree_flags_undeclared_capability
- tests/test_vet.py::TestScanTreeWithLocalSource::test_scan_tree_surfaces_a_cve_fingerprint_finding
- tests/test_vet.py::TestScanTreeMultipleLockfiles::test_scan_tree_scans_every_lockfile
- tests/test_vet.py::TestScanTreeTimeout::test_slow_package_returns_within_timeout_not_task_duration
designated_repro_test: null
threat: null
component: null
---
T-0202 fixed the check-path log-level bug (stdout handler defaulted to DEBUG unconditionally) and demoted the per-symbol/per-violation INFO calls found in gates/graph along that path. It did not exhaustively classify every _log./print( call site repo-wide (~1016 sites across src/frob) into keep-INFO/demote-DEBUG/convert-print as the ticket's enumerate-first instruction asked -- only src/frob/{gates,graph,check,app/check_runner.py,logging} got a full pass; the other 26 files under src/frob/app/ (89 INFO, 125 ERROR, 46 print call sites) and all non-scope dirs (strata 27, vet 17, fuzz 6, dup 5, tickets 4, testing 3, perf 3, lang 3, serve 2, arch 2, stats 1, release 1, policy 1, mutate 1, cve 1) were only sampled, not individually classified. Do the full pass and produce the classification table T-0202's Done report deferred.