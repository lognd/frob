---
id: T-1044
title: ffi_boundary gate missing from _STAGE_GROUPS breaks --stamp-baseline --only
  chunking
state: done
kind: bug
origin: agent
created: '2026-07-27'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/__init__.py
- tests/unit/test_app_runners_batch6.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_completes_and_stamps
designated_repro_test: null
threat: null
component: null
---
T-0690 registered ffi_boundary in frob.gates._ALL_GATES (38 gates total) but never added it to any _STAGE_GROUPS member, leaving it as a 1-gate leftover chunk that _stamp_baseline_gate_chunks() expects but no --only <group-or-gate> loop in the agent playbook enumerates by name, so the chunked accumulator in _run_stamp_baseline never converges (37/38 covered forever) and test_stamp_baseline_only_chunk_completes_and_stamps fails. Root cause of the reported main regression's 4th symptom; the other 3 reported failures (test_testing_collect, test_close_with_evidence_and_done_report_succeeds, test_dry_run_reports_clean) were NOT a code regression -- they were caused by a stray /tmp/pyproject.toml left on the shared machine tmp dir that uv discovered as a workspace root for any pytest tmp_path fixture nested under /tmp; removing that stray file made all three pass unmodified, confirmed by reproducing with and without it present.