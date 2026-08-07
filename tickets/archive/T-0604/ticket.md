---
id: T-0604
title: 'derived-state manifest: persist fingerprints and detect drift across runs'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0570
tier: ticket
sprint: null
scope:
- src/frob/doctor.py
- tests/system/test_cli_doctor.py
- docs/guides/install.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/guides/install.md
  reason: 'docs/guides/install.md#derived-state-integrity-manifest-t-0570 is where

    DerivedArtifactDrift and detect_derived_state_drift''s frob:doc anchor

    lives; the section still described T-0570''s reporting-only behavior and

    still pointed at "out of scope, see follow-up" for the block that T-0603

    already landed -- documenting the new drift symbols and correcting the

    stale sentence belongs in the same change as the code (frob:doc +

    docs in the same change).

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_first_run_reports_no_drift_and_writes_manifest
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_rewritten_artifact_between_two_runs_reports_drift
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_drift_is_informational_and_does_not_affect_healthy
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_unchanged_artifact_reports_no_drift
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_malformed_manifest_is_treated_as_no_prior_run
designated_repro_test: null
acceptance:
- text: GIVEN a derived artifact rewritten out-of-band between two doctor runs WHEN
    run_diagnosis executes THEN the drift is reported naming the artifact and both
    fingerprints
  evidence:
  - tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_first_run_reports_no_drift_and_writes_manifest
threat: null
component: null
---
T-0570 computes sha256 fingerprints per run and validates format (SQLite magic, JSON parse) but never persists them -- so content DRIFT between runs (an artifact silently rewritten by a stale tool or a foreign process) is undetectable; only malformed bytes are caught. Store the fingerprints in a manifest file and compare on the next doctor run, reporting any artifact whose hash changed without a corresponding legitimate producer run. Flagged by T-0570's reviewer as the gap between the ticket title's 'manifest' promise and the delivered check-on-read.