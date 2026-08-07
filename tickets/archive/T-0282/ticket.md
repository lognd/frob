---
id: T-0282
title: 'strata_core::reachable: terminal-edge support for non-transitive flow chains'
state: done
kind: security
origin: agent
created: '2026-07-19'
priority: medium
parent: T-0254
tier: ticket
sprint: null
scope:
- strata-core/src/lib.rs
- strata-core/strata_core.pyi
- src/frob/strata/_facts.py
- src/frob/strata/_krb.py
- tests/**
- docs/strata/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- strata-core/src/lib.rs::tests::non_transitive_edge_is_a_terminal_hop
- strata-core/src/lib.rs::tests::non_transitive_edge_may_still_be_the_final_hop_of_a_mixed_chain
- strata-core/src/lib.rs::tests::reachable_returns_witness_paths
- tests/unit/strata/test_facts.py::TestClosure::test_krb_no_transit_attr_stops_chaining_past_that_hop
- tests/unit/strata/test_krb.py::TestTrustChainReachability::test_non_transitive_chain_currently_over_reaches_known_gap
- tests/unit/strata/test_krb.py::TestTrustChainReachability::test_transitive_chain_reaches_across_both_hops
- tests/unit/strata/test_krb.py::TestKrbTrustFlows::test_sync
- tests/unit/strata/test_kernel_properties.py::test_reachable_matches_bfs_oracle
designated_repro_test: null
threat: elevation-of-privilege
component: null
---
SCOPE001 note: `strata-core/strata_core.pyi` added to scope alongside
`strata-core/src/lib.rs` -- the `.pyi` type stub for `reachable`'s `edges`
parameter must change in lockstep with the Rust `Edge` tuple's new 5th
`transitive` field (T-0134's ty-visible-signature contract for
`strata_core`); leaving it stale would silently desync the typed surface
from the actual PyO3 binding.