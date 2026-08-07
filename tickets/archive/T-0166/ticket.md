---
id: T-0166
title: store grammar rejects code/may despite surface.md implying support
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
- docs/strata/surface.md
- src/frob/strata/**
- tests/**
- design/frob.strata
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_store_code_may.py::TestStoreCodeMayGrammar::test_store_code_glob_elaborates_to_code_attr
- tests/unit/strata/test_store_code_may.py::TestStoreCodeMayGrammar::test_store_may_capability_lands_on_node_may
- tests/unit/strata/test_store_code_may.py::TestStoreMayFeedsThreat003::test_store_with_exec_may_fires_undischarged_cwe_94
designated_repro_test: null
threat: null
component: null
---
Confirmed twice (T-0150 review read parse_store directly: no code/may branch, falls through to unknown-store-property; typani pilot reconfirmed): stores cannot carry code/may declarations though docs/strata/surface.md implies they can. T-0150 worked around it by folding tickets_ledger's code into the core node. Fix properly: implement code/may on store_prop in strata-core (mirroring parse_node), elaborate into the kernel, un-fold frob's own tickets_ledger workaround in design/frob.strata, and correct surface.md either way so doc and grammar agree.