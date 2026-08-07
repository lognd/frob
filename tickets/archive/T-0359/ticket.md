---
id: T-0359
title: 'arch: exempt test files from advisory abstraction-opportunity/long-function
  categories'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- src/frob/gates/_arch.py
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestTestFileExemption::test_test_file_no_long_function_or_god_class
- tests/unit/test_arch.py::TestTestFileExemption::test_equivalent_src_file_still_flagged
- tests/unit/test_arch.py::test_arch_end_to_end_analyze_then_render
- tests/test_excludes.py::test_is_test_file_typescript_naming
designated_repro_test: null
threat: null
component: null
---
T-0204 family 1 (~51 warnings: 28 abstraction-opportunity + 23 long-function/god on TEST files). Test functions sharing signature (Path, MonkeyPatch) -> None and long arrange-act-assert bodies are the nature of tests, not production-architecture debt. Principled fix: exempt test files from frob-arch's advisory categories, mirroring how _design_files/TEST009 already exempts test fixtures via _is_test_file. Acceptance: frob-arch reports 0 abstraction-opportunity/long-function/god warnings on files under tests/, with the exemption implemented via a shared _is_test_file-style check (no ad hoc per-file waivers). NO blanket waiver; honest summary line.