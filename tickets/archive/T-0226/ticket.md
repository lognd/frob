---
id: T-0226
title: utility/non-transitive flow marking -- SYS003 hub edges destroy true noflow
  claims
state: done
kind: feature
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- strata-core/src/parse.rs
- docs/strata/**
- tests/**
- design/frob.strata
- tickets.md
- editors/vscode-strata/syntaxes/strata.tmLanguage.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_facts.py::TestClosure::test_utility_attr_stops_chaining_past_that_hop
- tests/unit/strata/test_facts.py::TestClosure::test_utility_attr_does_not_defeat_a_real_transitive_flow
- tests/unit/strata/test_litmus_utility_hub.py::TestUtilityHubVulnLitmus::test_unmarked_hub_edge_refutes_the_noflow_claim
- tests/unit/strata/test_litmus_utility_hub.py::TestUtilityHubHardenedLitmus::test_marked_utility_hub_edge_lets_the_noflow_claim_prove
- strata-core/src/parse/mod.rs::tests::parses_flow_utility
- strata-core/src/parse/mod.rs::tests::parses_flow_utility
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 11 (expressiveness): graphite had to withdraw a TRUE claim ('TUI never crosses HTTP') because SYS003 forced declaring tui->core (logging import) and core->server (entrypoint hosting), and reachability closure then refutes the noflow through the hub. Add a flow attribute (utility / no-transit) excluded from noflow transitive closure, or claim-level path exclusions; litmus pair: hub edge marked utility keeps the noflow claim provable, unmarked refutes it. Grammar change -> tmLanguage drift-lock will fire.

Scope widened post-start to include `editors/vscode-strata/syntaxes/strata.tmLanguage.json`: the ticket's own text anticipated the tmLanguage drift-lock firing, and `docs/guides/extending/strata-surface-grammar.md`'s add-an-entry recipe requires the SAME keyword land in both `parse.rs` and the tmLanguage grammar file in one change -- `tests/unit/test_strata_tmlanguage.py` checks parser-to-grammar keyword drift one-directionally, so adding `utility` to the parser without the grammar file would fail that existing test. `frob ticket sweep T-0226` re-run after this edit.