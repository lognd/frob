---
id: T-0368
title: 'arch: exempt test files + data fixtures from large-file/deep-nesting too'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/arch/
- src/frob/gates/_arch.py
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestLargeFile::test_large_test_file_not_flagged
- tests/unit/test_arch.py::TestLargeFile::test_large_src_file_still_flagged
- tests/unit/test_arch.py::TestLargeFile::test_fixtures_json_not_flagged
- tests/unit/test_arch.py::TestDeepNestingExemption::test_deeply_nested_test_file_no_finding
- tests/unit/test_arch.py::TestDeepNestingExemption::test_equivalent_src_file_still_flagged
designated_repro_test: null
threat: null
component: null
---
T-0359 exempted test files from arch abstraction-opportunity/long-function/god-class. Remaining: ~18 large-file + 2 deep-nesting arch warnings still fire on test files (test_gates.py etc.) and on pure DATA fixtures (tests/unit/cve/fixtures/*.json flagged large-file). Test files naturally grow large (many cases) and fixture JSON is data, not architecture. Extend the is_test_file exemption to large-file and deep-nesting for test files, and skip non-source data-fixture files (e.g. under tests/**/fixtures/, *.json) from arch large-file entirely. Do NOT exempt src. Acceptance: 0 arch findings on tests/** and on fixture data; src unchanged.