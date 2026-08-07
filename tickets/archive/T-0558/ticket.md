---
id: T-0558
title: 'graph: parse/IO failure silently erases a file''s entire obligation set (T-0404
  finding 2)'
state: done
kind: bug
origin: auditor
created: '2026-07-21'
priority: high
parent: T-0404
tier: ticket
sprint: null
scope:
- src/frob/graph/
- src/frob/gates/_parse_failures.py
- tests/test_gates.py
- src/frob/gates/__init__.py
- tests/test_graph.py
- pyproject.toml
- CHANGELOG.md
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_parse_failures.py
  reason: PARSE001 gate surfaces graph.GraphSnapshot.parse_failures (T-0558's fix)
    as a real check violation; new standalone module, additive-only registration lines
    in gates/__init__.py per this wave's gates/** ownership split
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_gates.py
  reason: PARSE001 gate regression tests
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/gates/__init__.py
  reason: additive-only registration lines (import + frozenset entry + canonical-order
    entry + lambda entry) wiring the new parse_failure_gate module into frob check,
    per this wave's gates/** ownership split
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_graph.py
  reason: PARSE001/T-0558 regression tests + re-tagging TestExclude/TestParseFailures
    test methods now that T-0544 is closed (COV002 needs an open-ticket edge)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: REL001 requires a version bump for T-0558's new public GraphSnapshot.parse_failures/ParseFailure/parse_failure_gate
    API
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: REL001 version-bump artifact
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 version-bump artifact (frob release stamp)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: mechanical lockfile refresh alongside version bump
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_graph.py::TestParseFailures::test_parse_error_is_recorded_as_parse_failure
- tests/test_graph.py::TestParseFailures::test_native_parser_unavailable_is_not_a_parse_failure
- tests/test_gates.py::TestParseFailureGate::test_parse_failure_is_an_error_violation
- tests/test_gates.py::TestParseFailureGate::test_no_parse_failures_is_clean
designated_repro_test: null
threat: null
component: null
---
docs/audits/lang-check-docs.md finding 2. _parse_source_file_fresh (graph/__init__.py) returns (True, (), (), ()) on any parse_file Err other than the expected NativeParserUnavailable degrade -- the file is recorded as successfully processed with zero symbols/edges, so every public symbol and every frob:doc/frob:invariant/frob:describes/frob:tests edge in it silently vanishes; COV001/exports/DRIFT/INV all pass vacuously for it. Repro: any file tree-sitter cannot parse at all -> gates green, design graph invisible. RIGHT-WAY fix: surface parse/IO failures as an ERROR-severity gate violation (a PARSE001-style rule) instead of a swallowed warning. Out of T-0404's declared scope (src/frob/graph/, not lang/check/gates/) -- needs a scope-widened or standalone follow-up ticket.