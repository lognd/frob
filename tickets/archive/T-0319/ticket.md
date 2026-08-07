---
id: T-0319
title: 'packaging: frob doctor subcommand to verify+remediate missing native extensions'
state: done
kind: feature
origin: human
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- docs/**
- tests/**
- pyproject.toml
- CHANGELOG.md
- .frob-release.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_doctor.py::test_run_diagnosis_natives_absent
- tests/test_doctor.py::test_run_diagnosis_natives_present
- tests/system/test_cli_doctor.py::TestDoctorCli::test_doctor_fails_loud_when_native_missing
designated_repro_test: null
threat: null
component: null
---
Follow-up from T-0316: no install-time guard exists against a plain 'uv tool upgrade frob' (or 'uv tool install --force --reinstall frob' without --with) silently stripping the strata_core/frob_core native extensions that 'make install-tool' added. T-0316 documents a manual 'python3 -c "import strata_core, frob_core"' check plus the loud SYS004/NativeExtensionUnavailable failure gates already provide as the honest fallback. This ticket is to build a real 'frob doctor' (or 'frob --version --verbose') subcommand that runs that same check, reports native-extension presence/version, and prints the exact 'make install-tool' remediation -- so the check is a first-class CLI surface instead of a paragraph in docs/guides/install.md. Also re-evaluate publishing strata-core/frob-core as real PyPI wheels (docs/guides/install.md 'Why not pip install frob[strata]?' section) as the actual long-term fix; that publish step needs PyPI project ownership/CI credentials this environment does not have, so it stays a separate decision, not blocking the doctor subcommand.