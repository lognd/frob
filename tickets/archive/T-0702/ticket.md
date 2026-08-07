---
id: T-0702
title: 'strata grammar: demand declarations (users/rate) with flow propagation and
  fan-in summation'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: T-0331
tier: ticket
sprint: null
scope:
- strata-core/src/parse.rs
- src/frob/strata/**
- editors/**
- docs/strata/**
- tests/unit/strata/
- design/frob.strata
- docs/strata/roadmap.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: AFFECT001/COV002 fix for T-0700's earlier waiver re-point touching these
    node blocks; frob:ticket added pointing at the tracked successor
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/strata/roadmap.md
  reason: AFFECT001 closure doc for the same design/frob.strata node changes
  actor: logan
  at: '2026-07-27'
evidence:
- strata-core/src/parse/mod.rs::tests::parses_node_users_and_rate
- strata-core/src/parse/mod.rs::tests::parses_node_without_users_or_rate_defaults_null
- strata-core/src/parse/mod.rs::tests::parses_node_users_only_no_rate
- strata-core/src/parse/mod.rs::tests::parses_store_users_and_rate
- strata-core/src/parse/mod.rs::tests::parses_node_rate_does_not_collide_with_capacity_rate
- tests/unit/strata/test_demand.py::TestAggregateDemand::test_two_entry_nodes_sum_at_fan_in
- tests/unit/strata/test_demand.py::TestAggregateDemand::test_no_demand_declared_is_undeclared_not_zero
- tests/unit/strata/test_demand.py::TestAggregateDemand::test_demand_declared_elsewhere_not_reaching_node_is_undeclared
- tests/unit/strata/test_demand.py::TestAggregateDemand::test_rate_and_users_compose_additively
- tests/unit/strata/test_demand.py::TestAggregateDemand::test_self_declaring_node_reports_its_own_demand
- tests/unit/strata/test_demand.py::TestAggregateDemand::test_fanout_multiplies_propagated_demand
- tests/unit/strata/test_demand.py::TestNodeUsersRateFields::test_node_defaults_to_none
- tests/unit/strata/test_demand.py::TestNodeUsersRateFields::test_node_accepts_explicit_users_and_rate
- tests/unit/strata/test_demand.py::test_store_users_and_rate_elaborate_same_as_node
- tests/unit/test_strata_tmlanguage.py::test_construct_keywords_match_parser_bidirectionally
- tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
- strata-core/src/parse/mod.rs::tests::parses_node_users_and_rate
- strata-core/src/parse/mod.rs::tests::parses_node_without_users_or_rate_defaults_null
- strata-core/src/parse/mod.rs::tests::parses_node_users_only_no_rate
- strata-core/src/parse/mod.rs::tests::parses_store_users_and_rate
- strata-core/src/parse/mod.rs::tests::parses_node_rate_does_not_collide_with_capacity_rate
designated_repro_test: null
acceptance:
- text: GIVEN two entry nodes declaring users 300k and 200k both flowing into one
    db resource WHEN elaboration runs THEN the db's aggregate demand is 500k and queryable;
    GIVEN no demand declared THEN the resource reports demand-undeclared, not zero
  evidence:
  - strata-core/src/parse/mod.rs::tests::parses_node_users_and_rate
  - strata-core/src/parse/mod.rs::tests::parses_node_without_users_or_rate_defaults_null
  - strata-core/src/parse/mod.rs::tests::parses_node_users_only_no_rate
  - strata-core/src/parse/mod.rs::tests::parses_store_users_and_rate
  - strata-core/src/parse/mod.rs::tests::parses_node_rate_does_not_collide_with_capacity_rate
  - tests/unit/strata/test_demand.py::TestAggregateDemand::test_two_entry_nodes_sum_at_fan_in
  - tests/unit/strata/test_demand.py::TestAggregateDemand::test_no_demand_declared_is_undeclared_not_zero
  - tests/unit/strata/test_demand.py::TestAggregateDemand::test_demand_declared_elsewhere_not_reaching_node_is_undeclared
  - tests/unit/strata/test_demand.py::TestAggregateDemand::test_rate_and_users_compose_additively
  - tests/unit/strata/test_demand.py::TestAggregateDemand::test_self_declaring_node_reports_its_own_demand
  - tests/unit/strata/test_demand.py::TestAggregateDemand::test_fanout_multiplies_propagated_demand
  - tests/unit/strata/test_demand.py::TestNodeUsersRateFields::test_node_defaults_to_none
  - tests/unit/strata/test_demand.py::TestNodeUsersRateFields::test_node_accepts_explicit_users_and_rate
  - tests/unit/strata/test_demand.py::test_store_users_and_rate_elaborate_same_as_node
  - tests/unit/test_strata_tmlanguage.py::test_construct_keywords_match_parser_bidirectionally
  - tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
  - strata-core/src/parse/mod.rs::tests::parses_node_users_and_rate
  - strata-core/src/parse/mod.rs::tests::parses_node_without_users_or_rate_defaults_null
  - strata-core/src/parse/mod.rs::tests::parses_node_users_only_no_rate
  - strata-core/src/parse/mod.rs::tests::parses_store_users_and_rate
  - strata-core/src/parse/mod.rs::tests::parses_node_rate_does_not_collide_with_capacity_rate
threat: null
component: null
---
User mandate 2026-07-22 (starvation semantics prerequisite): the model has no notion of LOAD, so an exclusive lock and an exclusive lock behind 500k users look identical. Add: (1) demand declarations on entry nodes -- users N (steady population) and/or rate N per_s (arrival rate), parse.rs node/store symmetry per T-0261; (2) propagation: demand flows along existing Flow edges, SUMMING at fan-in, so any node/resource can be asked 'what aggregate demand reaches you' (elaboration-time computation, queryable like effects); (3) optional capacity/holding-time hints on resources and arbiters (capacity N, holds MS) with documented defaults; (4) tmLanguage + docs/strata section + litmus fixtures (propagation sums correctly across fan-in/fan-out, missing demand is distinguishable from zero demand). Consumers (utilization/starvation obligations) are the sibling ticket.