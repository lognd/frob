---
id: T-0294
title: 'DSL parser: eliminate 13 malformed-directive false positives (secret-fake
  marker, kinds, trailing prose)'
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
blocked_by:
- T-0286
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/dsl.py
- src/frob/gates/_secrets.py
- tests/**
- src/frob/fuzz/**
- src/frob/app/perf_runner.py
- docs/modules/graph.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/graph/test_dsl.py::TestReservedMarkerVerbs::test_secret_fake_is_silently_skipped
- tests/unit/graph/test_dsl.py::TestReservedMarkerVerbs::test_unreserved_unknown_verb_still_reports_malformed
- tests/system/test_cli_check.py::TestCheckTicketScopedAlwaysReportsOnFailure::test_ticket_scoped_nonzero_exit_has_diagnostic_output
- tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map
- tests/test_dup_rungs.py::TestR6Probing::test_fires_on_equivalent_functions_with_renamed_multi_arg_params
- tests/test_gates.py::TestCoverageLoad::test_parses_line_to_symbol_span
designated_repro_test: null
acceptance:
- text: given the intentional frob:secret-fake fixture marker (_secrets.py _FAKE_MARKER,
    a deliberately-unregistered literal the secrets gate scans for), when parse_directives
    sees it, then it is recognized as a RESERVED marker and skipped silently -- no
    "unknown verb secret-fake" malformed-directive warning (3 occurrences in test_secrets_gate.py
    cleared)
  evidence: []
- text: given a frob:tests directive with kind=drift or kind=system, when parsed,
    then either the kind is corrected to a valid unit/integration/e2e value in the
    3 real directives (test_selfconform.py x2 drift-lock=unit, test_cli_check.py system=e2e),
    so no invalid-kind warning fires
  evidence: []
- text: 'given the 7 directives with same-line trailing prose (frob:ticket/frob:todo/frob:tests
    followed by -- prose or bare prose: perf_runner.py, fuzz/_arbitrary.py, fuzz/_run.py,
    test_dup_rungs.py x3, test_gates.py), when parsed under the T-0286 continuation/prose-tolerance
    rule, then the prose is accepted (or the directives are split) with no bad-attribute-syntax
    warning'
  evidence: []
- text: given a full frob check, when the graph is built, then the malformed-directive
    warning count from these 13 sources is ZERO
  evidence: []
threat: null
component: null
---
Investigated 2026-07-19: the 13 "malformed directive" warnings are NOT sloppy comments -- they are a DSL-parser robustness gap in three classes. (1) frob:secret-fake is an INTENTIONAL cross-subsystem literal marker (src/frob/gates/_secrets.py:15,66 -- "unregistered marker, the literal substring frob:secret-fake"); the secrets gate scans for it to discharge a fixture token, but graph/dsl.py::parse_directives treats frob:<anything> as a directive and warns "unknown verb secret-fake". Fix: reserve secret-fake (and audit for any other intentional literal markers) as a known no-op verb the parser skips silently -- the two subsystems must agree on the vocabulary. (2) Three real frob:tests directives use kind=drift/system, outside the unit/integration/e2e enum -- correct them (a drift-lock conformance test is unit; a CLI system test is e2e). (3) Seven directives carry same-line explanatory prose (frob:ticket T-0027 -- propagate...; frob:todo T-0002 registry is process-global...) that the attr parser rejects; this is the SAME ergonomic gap as T-0286 (multi-line/prose-tolerant reasons), hence blocked_by T-0286 -- once prose/continuation is tolerated, split or annotate these. NOTE scope collision: fuzz/_arbitrary.py and fuzz/_run.py are also touched by the in-flight core-commands arch burndown -- sequence this ticket AFTER that merges, or coordinate, to avoid a conflict. This is the right fix: papering the warnings over by mangling test comments would hide a real parser/secrets-gate vocabulary disagreement.