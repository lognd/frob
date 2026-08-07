---
id: T-1501
title: 'doctor.py run_diagnosis split: extract _assemble_doctor_report (ARCH001)'
state: done
kind: docs
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/doctor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_doctor.py::test_run_diagnosis_reports_stale_binary_floor
- tests/test_doctor.py::test_run_diagnosis_stale_binary_none_when_no_floor
- tests/unit/test_config.py::test_stale_binary_warning_flags_version_below_floor
- tests/test_natives.py::TestNativeAutorebuild::test_disabled_via_env_var_skips_autorebuild
- tests/unit/strata/test_selfconform.py::TestLanguageCoverageDriftLock::test_scanned_languages_equals_registry_languages
designated_repro_test: null
threat: null
component: null
---
land-repair for w17a-uxmisc: src/frob/doctor.py::run_diagnosis tripped
ARCH001 (121 lines vs 60-line threshold) even after T-1162's prior split,
because the accumulated per-ticket historical narrative in its docstring
(T-0604/T-0857/T-1132/T-1131/T-1161/T-1218 paragraphs) counts toward the
threshold along with the body. Fixed by extracting the healthy/DoctorReport
assembly into a new _assemble_doctor_report helper and trimming the
docstring's historical trail down to a summary paragraph. Filed as a real
ticket so run_diagnosis's docstring can cite it instead of a wrong/reused id.