---
id: T-1440
title: 'strata: scoped may clauses -- a capability grant must name its surface, not
  bless the whole node'
state: done
kind: feature
origin: human
created: '2026-08-02'
priority: high
parent: null
tier: story
sprint: null
scope:
- src/frob/strata/**
- strata-core/src/parse/**
- design/frob.strata
- docs/strata/**
- tests/unit/strata/test_parse.py
- tests/unit/strata/test_effects.py
- strata-core/src/lib.rs
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_parse.py
  reason: the delivered grammar+join portion binds evidence in these two test files
    and touches the strata-core crate root; adds were refused mid-work by T-1420's
    since-released standing lease
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/strata/test_effects.py
  reason: the delivered grammar+join portion binds evidence in these two test files
    and touches the strata-core crate root; adds were refused mid-work by T-1420's
    since-released standing lease
  actor: logan
  at: '2026-08-02'
- op: add
  glob: strata-core/src/lib.rs
  reason: the delivered grammar+join portion binds evidence in these two test files
    and touches the strata-core crate root; adds were refused mid-work by T-1420's
    since-released standing lease
  actor: logan
  at: '2026-08-02'
evidence:
- tests/unit/strata/test_parse.py::TestParseModule::test_may_via_scopes_a_grant_to_sub_globs
- tests/unit/strata/test_parse.py::TestParseModule::test_may_via_also_parses_on_store
- tests/unit/strata/test_effects.py::TestScopedMayViaConformance::test_observation_outside_via_surface_is_a_violation
- tests/unit/strata/test_effects.py::TestScopedMayViaConformance::test_observation_inside_every_via_surface_is_clean
- tests/unit/strata/test_effects.py::TestScopedMayViaConformance::test_via_less_grant_still_covers_the_whole_node
- tests/unit/strata/test_effects.py::TestScopedMayViaConformance::test_legacy_node_with_no_may_grants_falls_back_to_whole_node
- tests/unit/strata/test_effects.py::TestScopedMayViaConformance::test_scoped_and_via_less_grants_of_different_kinds_compose
designated_repro_test: null
acceptance:
- text: GIVEN a node with may X via glob WHEN a file outside the glob observes X THEN
    SYS100 fires for that file even though the node declares X
  evidence:
  - tests/unit/strata/test_parse.py::TestParseModule::test_may_via_scopes_a_grant_to_sub_globs
  - tests/unit/strata/test_parse.py::TestParseModule::test_may_via_also_parses_on_store
  - tests/unit/strata/test_effects.py::TestScopedMayViaConformance::test_observation_outside_via_surface_is_a_violation
  - tests/unit/strata/test_effects.py::TestScopedMayViaConformance::test_observation_inside_every_via_surface_is_clean
  - tests/unit/strata/test_effects.py::TestScopedMayViaConformance::test_via_less_grant_still_covers_the_whole_node
  - tests/unit/strata/test_effects.py::TestScopedMayViaConformance::test_legacy_node_with_no_may_grants_falls_back_to_whole_node
  - tests/unit/strata/test_effects.py::TestScopedMayViaConformance::test_scoped_and_via_less_grants_of_different_kinds_compose
- text: GIVEN a node with may X via glob WHEN only files inside the glob observe X
    THEN the audit is green
  evidence:
  - tests/unit/strata/test_parse.py::TestParseModule::test_may_via_scopes_a_grant_to_sub_globs
  - tests/unit/strata/test_parse.py::TestParseModule::test_may_via_also_parses_on_store
  - tests/unit/strata/test_effects.py::TestScopedMayViaConformance::test_observation_outside_via_surface_is_a_violation
  - tests/unit/strata/test_effects.py::TestScopedMayViaConformance::test_observation_inside_every_via_surface_is_clean
  - tests/unit/strata/test_effects.py::TestScopedMayViaConformance::test_via_less_grant_still_covers_the_whole_node
  - tests/unit/strata/test_effects.py::TestScopedMayViaConformance::test_legacy_node_with_no_may_grants_falls_back_to_whole_node
  - tests/unit/strata/test_effects.py::TestScopedMayViaConformance::test_scoped_and_via_less_grants_of_different_kinds_compose
acceptance_amendments:
- op: remove
  index: 2
  old_text: GIVEN a via-less may on a node binding more files than the threshold WHEN
    frob sys audit runs THEN an advisory finding names the unscoped grant
  new_text: null
  reason: split to the advisory-rule child ticket filed in this worktree (via-less-grant
    advisory + require_may_scope escalation); the delivered portion covers the grammar
    and the per-file SYS100 join, acceptance [0]/[1], both bound
  actor: logan
  at: '2026-08-02'
threat: null
component: null
---
User directive 2026-08-02: the current may clause grants a capability to a node's ENTIRE code glob, which reproduces the anti-pattern strata exists to kill -- everything inside a broad node (testsuite: code tests/**) can do everything the node may. A grant should be forced down to a few controllable surfaces. Design sketch: (1) grammar -- may KIND [via GLOB[, GLOB...]] where via names sub-globs of the node's own code binding; a via-less may keeps meaning whole-node for migration. (2) SYS100 join becomes per-file: an observation in file F is discharged only by a may whose via matches F (or a via-less may); an observation outside every via surface stays red even though the node nominally holds the capability. (3) SYS101 staleness likewise judged per via surface, so a dead grant on one file is flagged even while another file legitimately uses the same kind. (4) a new advisory rule fires on via-less may clauses on nodes whose code glob binds more than a threshold file count, driving the codebase toward full scoping without a flag-day; [strata] config gets require_may_scope to escalate it to error for repos ready to commit. (5) argument-level scoping (may env.read of FROB_*) is a natural follow-up once via lands; note it in docs but do not build it in this ticket. Migration for this repo: split testsuite/broad nodes' grants down to the actual observing files using the existing scanner's per-file observation data, which already knows exactly which file observes which kind.