---
id: T-0851
title: 'frob check: FMT001 gate for non-canonical frob: directive lines (T-0441 follow-up)'
state: done
kind: feature
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/check/**
- docs/modules/gates.md
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'FMT001 registration in _KNOWN_GATE_RULES requires a matching

    docs/design/registry/check-coverage.yaml gate_rule_entries entry

    (REGISTRY001 exhaustiveness) plus a gate_rule_total bump -- the same

    mechanical requirement every other _KNOWN_GATE_RULES addition carries,

    not a separate feature.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates.py::TestFmt001Gate::test_directive_run_over_limit_flagged
- tests/test_gates.py::TestFmt001Gate::test_ordinary_long_comment_not_flagged
- tests/test_gates.py::TestFmt001Gate::test_long_code_line_not_flagged
- tests/test_gates.py::TestFmt001Gate::test_untouched_line_not_flagged
- tests/test_gates.py::TestFmt001Gate::test_short_directive_not_flagged
designated_repro_test: null
threat: null
component: null
---
T-0441 built `frob fmt` (canonical-form wrap/unwrap of frob: directive
comment lines, src/frob/gates/_fmt_directives.py) but did NOT wire a
`frob check` gate rule for it -- src/frob/check/ and the gate
stage/rule-catalog in src/frob/gates/__init__.py were outside T-0441's
declared scope.

Add a gate (e.g. FMT001) that fires when a diff-touched frob: directive
comment line exceeds the project's configured line length, with a
remediation hint: "directive line over NN cols; run `frob fmt` to wrap"
-- same self-remedying-message contract as every other gate. Reuse
frob.gates._fmt_directives.canonicalize_text/read_line_length; do not
re-derive the wrap logic.