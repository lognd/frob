---
id: T-0295
title: 'arch: strata long-function burndown to zero'
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/unit/strata/test_krb.py::TestTrustChainReachability::test_non_transitive_chain_currently_over_reaches_known_gap
- tests/unit/strata/test_facts.py::TestClosure::test_krb_no_transit_attr_stops_chaining_past_that_hop
designated_repro_test: null
acceptance:
- text: given `frob arch .`, when scoped to src/frob/strata/_export.py, _facts.py,
    _host.py, _host_isolation.py, _infra.py, then zero long-function warnings remain
    (measured; see Done report for before/after counts)
  evidence: []
- text: given `frob check --only coverage`, when run after the change, then 0 COV001/errors
    (one displacement caught and fixed -- `elaborate_infra`'s frob:doc directive had
    landed on a newly-inserted helper above it)
  evidence: []
- text: given `uv run pytest tests/unit/strata -k "export or facts or host or infra"`,
    then all pass with no behavior change
  evidence: []
threat: null
component: null
---
