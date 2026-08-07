---
id: T-0956
title: 'strata design: re-point T-0700 live-tracker waivers, arbitrate tickets_ledger
  with new grammar'
state: done
kind: docs
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- design/**
- tests/test_tickets_live_tracker.py
- docs/strata/roadmap.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/strata/roadmap.md
  reason: AFFECT001 requires updating the roadmap.md self-hosting-commitments-decision-d7
    doc anchor when design/frob.strata's cli/gates/fleet/core/serve nodes change
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/unit/strata/test_access.py::TestResourceContentionViolations::test_arbitrated_by_discharges
- tests/unit/strata/test_access.py::TestResourceContentionViolations::test_lock_discharges
- tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_two_writers_fires_mode_blind
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
designated_repro_test: null
threat: null
component: null
---
T-0700 shipped access modes + resource/arbitrated_by grammar. design/frob.strata has 5 SYS203 "tickets_ledger" waivers explicitly written "re-evaluate at T-0700" (lines ~116/181/311/388/508) since the ledger genuinely has an arbiter (every writer serializes through .frob/tickets.lock, T-0458/T-0633) that SYS203 could not express until now. Re-express this properly: declare a `resource tickets_ledger { lock "tickets.lock" }` (or `arbitrated_by` the CLI-writer node, whichever models T-0458/T-0633's actual single-writer-lock discipline more accurately) plus `access "tickets_ledger" mode write` on each node/store that writes it, then drop the now-superseded SYS203 waivers once the model-level arbiter discharges the contention cleanly (verify via frob.strata._access.resource_contention_violations against frob's own elaborated design). Also re-point tests/test_tickets_live_tracker.py:220's `ticket=T-0700` placeholder to this ticket's id once assigned. Blocked by nothing; T-0700 is done and closed.