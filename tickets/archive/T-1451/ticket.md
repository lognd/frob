---
id: T-1451
title: 'strata: advisory rule + require_may_scope for via-less may on large nodes'
state: done
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- docs/design/registry/check-coverage.yaml
- design/litmus/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory::test_via_less_grant_on_large_node_fires
- tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory::test_via_less_grant_on_small_node_is_silent
- tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory::test_via_scoped_grant_on_large_node_is_silent
- tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory::test_node_with_no_may_never_fires
- tests/unit/strata/test_scope_config.py::TestStrataScopeConfig::test_missing_frob_toml_returns_defaults
- tests/unit/strata/test_scope_config.py::TestStrataScopeConfig::test_parses_strata_table
- tests/unit/strata/test_scope_config.py::TestStrataScopeConfig::test_malformed_toml_falls_back_to_defaults
- tests/unit/strata/test_scope_config.py::TestStrataScopeConfig::test_wrong_typed_strata_table_falls_back_to_defaults
- tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_sys107_defaults_to_warn
- tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_sys107_escalates_to_error_under_require_may_scope
- tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_other_sub_rules_stay_error_regardless_of_config
- tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_selfaudit_violation_carries_sys107_warn_severity
designated_repro_test: null
threat: null
component: null
---
T-1440 parent: (4) advisory rule on via-less may grants on large nodes,
plus [strata] require_may_scope escalation. Design sketch item 4: "a new
advisory rule fires on via-less may clauses on nodes whose code glob
binds more than a threshold file count, driving the codebase toward full
scoping without a flag-day; [strata] config gets require_may_scope to
escalate it to error for repos ready to commit." Not built by T-1440's
own landing (grammar/model plumbing + per-file SYS100 join only). Plan:
new SYS1xx rule id (register in docs/design/registry/check-coverage.yaml
and _KNOWN_GATE_RULES per the playbook's one-documented-entry rule,
never duplicate); threshold constant (file count over a node's bound
`code` globs, precedent: existing LARGE001-style thresholds elsewhere in
this codebase); a `[strata]` config section reader (frob.toml) for
`require_may_scope` (bool or per-repo threshold override) that escalates
the finding from WARN/advisory to ERROR. Needs its own litmus fixture
under design/litmus/ per this repo's grammar-testing precedent.