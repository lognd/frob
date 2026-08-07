---
id: T-0904
title: Add regression test/lint for lang/** parse size+timeout guard
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/lang/__init__.py
- tests/unit
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_lang_parse_guard.py::TestParseGuardIsWired::test_parse_source_calls_the_guard_helpers
- tests/unit/test_lang_parse_guard.py::TestParseGuardIsWired::test_parse_strata_file_source_calls_the_guard_helpers
- tests/unit/test_lang_parse_guard.py::TestParseGuardIsInvoked::test_python_file_invokes_size_cap_and_timeout
- tests/unit/test_lang_parse_guard.py::TestParseGuardIsInvoked::test_strata_file_invokes_size_cap_and_timeout
designated_repro_test: null
threat: null
component: null
---
Found while working T-0786 (gate-vacuousness sweep), pairs with the
lang/** file-size/timeout guard fix ticket.

Add a regression test (and, if practical, a static lint) asserting every
`frob.lang` parse entrypoint (`parse_file`/`_parse`/`_parse_strata_file`)
enforces a bounded size/time budget before/around the actual
tree-sitter/strata-core parse call -- so a future refactor cannot silently
drop the guard the paired fix ticket adds.