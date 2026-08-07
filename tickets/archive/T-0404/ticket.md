---
id: T-0404
title: 'AUDIT: polyglot enforcement + fail-closed parsing/docs (docs/audits/lang-check-docs.md)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0397
tier: ticket
sprint: null
scope:
- src/frob/lang/
- src/frob/check/
- src/frob/gates/
- tests/test_gates.py
- tests/unit/test_check.py
- tests/unit/test_check_tool_unavailable.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: unit tests for DSL001/vitest-warn/detect_project_type fixes made by this
    audit ticket
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_check.py
  reason: unit tests for DSL001/vitest-warn/detect_project_type fixes made by this
    audit ticket
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_check_tool_unavailable.py
  reason: unit tests for DSL001/vitest-warn/detect_project_type fixes made by this
    audit ticket
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates.py::TestDsl001::test_malformed_frob_doc_directive_flagged
- tests/test_gates.py::TestDsl001::test_waive_reason_and_tests_kind_not_double_flagged
- tests/unit/test_check_tool_unavailable.py::TestVitestUnverifiedZeroExit::test_run_vitest_warns_on_unparseable_zero_exit
- tests/unit/test_check.py::TestDetectProjectType::test_package_json_alone_is_typescript
designated_repro_test: null
threat: null
component: null
---
See docs/audits/lang-check-docs.md. HIGH: doc/coverage/drift/inv gates run ONLY in the Python pipeline -- a Rust/C++/TS repo gets ZERO COV/DOC/DRIFT despite the polyglot promise; parse/IO failure silently erases a files whole obligation set (gates pass vacuously); COV001 is WARN-only. RIGHT-WAY fix: run the accounting gates across ALL language pipelines; fail-closed + loud on parse/IO failure (never empty-as-clean); decide COV001 severity. Then re-audit until empty. MED/LOW in the doc.