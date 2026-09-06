---
id: T-3925
title: wire LANGUAGE_COLLECTORS into evidence BINDING (add/replace/land re-verify),
  not just verify
state: in-progress
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_tickets_evidence_cli.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_evidence_cli.py
  reason: end-to-end regression test mirroring TestTicketEvidenceRustOracle, using
    vitest -- the exact shape the consumer report (F-134) hit
  actor: logan
  at: '2026-09-05'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-134/F-039 recurrence (logand.app-v2): frob ticket evidence/close still reject vitest node ids for feature tickets. T-3847 wired LANGUAGE_COLLECTORS into VERIFICATION (_verify_ids_passing/_verify_unbucketed_ids) but not into the three BINDING/RESOLUTION call sites that build the collected set handed to add_evidence/replace_evidence/land's post-merge re-check:
  - _evidence_apply_node_ids (src/frob/app/ticket_runner/_verify.py) builds collected_ids = python_ids | rust_ids, passed to add_evidence's collected= param -> _check_evidence_resolution -> matches_collected. A vitest id is not in that set and is rejected as Err(UnknownEvidence) before verification is ever consulted.
  - _apply_replace_evidence (same file) has the identical python_ids | rust_ids pattern feeding replace_evidence.
  - _land_collected_fn (src/frob/app/ticket_runner/_land_cmd.py) has the identical pattern feeding frob.tickets._land_verify's D-05 post-merge resolution check (matches_collected again).
Fix: extend the collected set at all three sites to include every OTHER registered LANGUAGE_COLLECTORS entry (cpp/kotlin/ts today), best-effort per language (a collector Err logs and contributes nothing, never blocks binding), same posture _verify_unbucketed_ids already established. Do NOT fork matches_collected (D-11: gates and tickets deliberately share one copy) -- the fix belongs in how the collected SET is built, not in the matcher. Re-confirm (no code change expected) that _evidence.py:1395's collected=None warn-only path is now reserved for genuine opt-out callers, not a symptom of a missing language collector, since all three real CLI paths now supply a concrete multi-language set.