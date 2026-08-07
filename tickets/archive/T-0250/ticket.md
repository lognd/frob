---
id: T-0250
title: extend waive clause grammar to store nodes (tickets_ledger LINT004 gap from
  T-0166)
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- strata-core/src/parse.rs
- src/frob/strata/_ast.py
- src/frob/strata/_models.py
- src/frob/strata/_infra.py
- design/frob.strata
- docs/strata/waive.md
- tests/**
- editors/vscode-strata/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_infra.py::TestStoreWaivers::test_multi_instance_family_with_sub_target_elaborates_cleanly
- tests/unit/strata/test_infra.py::TestStoreWaivers::test_multi_instance_family_without_sub_target_fails_closed
- tests/unit/strata/test_litmus_waive_store.py::TestWaiveStoreLitmus::test_matched_store_waiver_suppresses_the_finding
designated_repro_test: null
threat: null
component: null
---
T-0166 (fix(tickets): land T-0166 store grammar rejects code/may despite surface.md implying support) added real code/may declarations to design/frob.strata's tickets_ledger store, including may "exec" with no kill switch -- this now fires a genuine LINT004 gap (frob sys audit exits 1) that T-0174's waive mechanism cannot suppress because the waive clause was only added to strata-core/src/parse/mod.rs::parse_node, not parse_store (T-0174's declared scope did not include store grammar work). Extend waive to store the same way T-0166 extended code/may to store (parse_store, StoreDecl, _elaborate_store), then waive tickets_ledger's LINT004 with reason pointing at T-0200, mirroring checker/core/stratamod/vet's existing waivers. Until this lands, frob sys audit honestly reports this one named gap rather than silently or fictitiously passing.