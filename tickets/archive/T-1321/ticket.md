---
id: T-1321
title: 'CI-env test hermeticity: doctor scaffold fold, ledger-commit git identity,
  serial-pools install leak'
state: done
kind: bug
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_doctor.py
- tests/test_prework_parity.py
- tests/unit/perf/test_serial_pools.py
- src/frob/tickets/_leases.py
- .github/workflows/ci.yml
- tests/test_tickets_leases.py
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_leases.py
  reason: 'scope closure: _leases.py identity-fallback change must carry its lease
    test file'
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_ticket_leases.py
  reason: 'scope closure: second lease test file covering _leases.py symbols'
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_doctor.py::test_run_diagnosis_natives_present
- tests/test_doctor.py::test_run_diagnosis_natives_absent
- tests/test_doctor.py::test_run_diagnosis_partial_availability
- tests/test_prework_parity.py::TestCliStartRecordsGateCompatibleDigest::test_start_then_gate_is_clean
- tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_identity_less_environment_falls_back_to_throwaway_git_identity
- tests/unit/perf/test_serial_pools.py::TestInstallSerialPools::test_without_serial_pools_worker_is_unattributed
- tests/unit/perf/test_serial_pools.py::TestInstallSerialPools::test_with_serial_pools_worker_is_majority_attributed
designated_repro_test: null
threat: null
component: null
---
Three CI-only pytest failures (seen at v0.277.0, all still latent because the causes are environmental, not code that later lands fixed): (1) tests/test_doctor.py run_diagnosis tests assert healthy=True / exact REMEDIATION_HINT against the REAL checkout; doctor folds scaffold conformance into healthy, and a fresh CI clone has the 3 git-hook managed blocks missing (hook-pre-commit, hook-pre-merge-commit, hook-reference-transaction-stash-guard) -- monkeypatch the scaffold/derived scans so the natives tests test natives only. (2) tests/test_prework_parity.py e2e drives frob ticket new in a tmp repo; T-1130 auto-commit runs plain git commit and CI runners have no user.name/user.email, so the ledger commit fails rc=128 (local passes via the developer's global config) -- set identity in the test fixture repo AND consider a -c user.name/user.email fallback in _add_and_commit_tickets_md for identity-less environments. (3) tests/unit/perf/test_serial_pools.py baseline test_without_serial_pools_worker_is_unattributed got fraction 0.45 in CI: install_serial_pools() patches concurrent.futures globally and no test uninstalls it, so full-suite ordering can leak the patch into the baseline -- add an uninstall/restore fixture around every install_serial_pools() caller. Verified 2026-07-29: all six failing tests pass locally in isolation on main, so the remaining exposure is purely environmental/ordering.