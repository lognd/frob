---
id: T-0570
title: 'derived-state integrity manifest: doctor-first fingerprint check for every
  derived artifact'
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/doctor.py
- docs/guides/install.md
- tests/system/test_cli_doctor.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/doctor.py
  reason: scope was empty at dispatch; this is where the manifest check + DoctorReport
    extension lives
  actor: logan
  at: '2026-07-22'
- op: add
  glob: docs/guides/install.md
  reason: frob:doc home for doctor.py public symbols; T-0554/T-0177 hold live leases
    on src/frob/check/ and src/frob/app/ so this ticket avoids both and keeps the
    manifest logic in doctor.py itself
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/system/test_cli_doctor.py
  reason: existing doctor test file, extends coverage for the new manifest check
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tickets.md
  reason: Done report ledger, always in scope
  actor: logan
  at: '2026-07-22'
evidence:
- tests/system/test_cli_doctor.py::TestDoctorCli::test_doctor_reports_healthy_when_natives_present
- tests/system/test_cli_doctor.py::TestDoctorCli::test_doctor_json_reports_healthy_when_natives_present
- tests/system/test_cli_doctor.py::TestDoctorCli::test_doctor_fails_loud_when_native_missing
- tests/system/test_cli_doctor.py::TestDoctorCli::test_doctor_json_fails_loud_when_native_missing
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_reports_absent_as_healthy
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_flags_corrupt_sqlite_cache
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_flags_malformed_json_stamp
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_accepts_valid_json_stamp
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_run_diagnosis_unhealthy_when_derived_state_corrupt
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_run_diagnosis_healthy_with_no_derived_state
designated_repro_test: null
threat: null
component: null
---
Three incidents: stale fixture dup.db silently flipped detector results (T-0517), make coverage clobbered natives producing 44 phantom check errors, coverage stamp lagging source. One mechanism: a manifest of derived artifacts (cache.db, dup.db, coverage-stamp, natives, pytest/cargo-collect, goldens) each with a content/version fingerprint, verified by doctor BEFORE any gate reports; on mismatch, one clear banner line instead of dozens of misleading findings. Scope: src/frob/doctor.py, src/frob/check/, .frob layout docs.