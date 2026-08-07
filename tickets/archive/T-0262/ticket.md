---
id: T-0262
title: 'std.krb: Kerberos/AD domain trust, SPNs, and delegation as first-class strata'
state: done
kind: security
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0255
parent: T-0254
tier: ticket
sprint: null
scope:
- strata-core/src/parse.rs
- src/frob/strata/**
- editors/**
- docs/strata/**
- tests/**
- tickets.md
- CHANGELOG.md
- pyproject.toml
- .frob-release.json
- strata-core/Cargo.lock
- frob-core/Cargo.lock
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
- tests/unit/strata/test_krb.py::TestKrbAttrs::test_desugars
- tests/unit/strata/test_krb.py::TestKrbAttrs::test_no_clauses_desugars_to_empty
- tests/unit/strata/test_krb.py::TestKrbManifest::test_reads
- tests/unit/strata/test_krb.py::TestKrbManifest::test_node_with_no_krb_attrs_returns_none
- tests/unit/strata/test_krb.py::TestKrbTrustFlows::test_sync
- tests/unit/strata/test_krb.py::TestKrbTrustFlows::test_two_way_synthesizes_reverse_edge_too
- tests/unit/strata/test_krb.py::TestKrbTrustFlows::test_no_trusts_synthesizes_nothing
- tests/unit/strata/test_krb.py::TestFlowAuthVia::test_read
- tests/unit/strata/test_krb.py::TestFlowAuthVia::test_flow_with_no_krb_attrs_returns_none
- tests/unit/strata/test_litmus_krb.py::TestKrbDeclaredLitmus::test_declared_manifest_round_trips_every_field
- tests/unit/strata/test_litmus_krb.py::TestKrbDeclaredLitmus::test_two_way_transitive_trust_synthesizes_both_directions
- tests/unit/strata/test_litmus_krb.py::TestKrbDeclaredLitmus::test_flow_authenticates_via_reads_ticket_kind
- tests/unit/strata/test_litmus_krb.py::TestKrbDeclaredLitmus::test_kdc_node_manifest_has_no_delegation
- tests/unit/strata/test_litmus_krb.py::TestKrbUndeclaredLitmus::test_undeclared_node_has_no_manifest
- tests/unit/strata/test_krb.py::TestKrbValidation::test_spn_without_runs_as_is_malformed
- tests/unit/strata/test_krb.py::TestKrbValidation::test_spn_with_runs_as_elaborates_cleanly
- tests/unit/strata/test_krb.py::TestTrustChainReachability::test_transitive_chain_reaches_across_both_hops
- tests/unit/strata/test_krb.py::TestTrustChainReachability::test_non_transitive_chain_currently_over_reaches_known_gap
designated_repro_test: null
threat: elevation-of-privilege
component: null
---
T-0254 auth pillar. Model the Kerberos/Active-Directory layer that sits between OS principals and the backend so domain auth becomes provable architecture. New std.krb vocabulary: a realm/domain and its KDC as trust-lattice nodes; a service principal name (SPN) bound to a service account (the runs_as / windows service account from T-0255/T-0261); an authenticates-via edge (a flow crosses a Kerberos boundary -- ticket-granting, service-ticket); and DELEGATION as an explicit, typed declaration -- none | constrained target=<spn-set> | rbcd | unconstrained. Delegation is the crown-jewel modeling target because it is the classic movement vector. Domain trusts (one-way/two-way, transitive) join the lattice so cross-realm reachability is model-checked. Elaborate into the KernelModel so existing flow/noflow/reach machinery applies to ticket flows. This ticket is the MODEL + vocabulary only; the delegation-abuse obligations live in T-0263. Grammar + tmLanguage drift-lock, litmus, docs/strata/krb.md. std.krb must compose with both linux (MIT/Heimdal keytabs) and windows (AD) host backends.