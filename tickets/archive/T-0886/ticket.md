---
id: T-0886
title: 'gates: real ctest source-accurate collection so the cpp structural fallback
  can retire'
state: done
kind: feature
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/_collect.py
- src/frob/gates/__init__.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCppSourceAccurateCollection::test_single_source_target_is_source_accurate
- tests/test_gates.py::TestCppSourceAccurateCollection::test_multi_source_target_falls_back_loudly
- tests/test_gates.py::TestCppSourceAccurateCollection::test_no_compile_commands_falls_back_loudly
- tests/test_gates.py::TestCppSourceAccurateCollection::test_gtest_discover_tests_include_and_dot_names
designated_repro_test: null
threat: null
component: null
---
T-0730 wires `collect_ts_tests`/`collect_cpp_tests` into `frob.gates._load_tests`
and retires the ts structural fallback (`_NATIVE_TEST_EXTENSIONS`) now that a real
vitest-backed node id can match a TS `frob:tests` directive's `path::name` symref
exactly.

C/C++ could not be retired in the same pass: `collect_cpp_tests`'s own docstring
discloses a KNOWN APPROXIMATION -- a ctest node id anchors to the build directory
(`<build_dir>::<test name>`), not the real source file a `frob:tests` directive
lives above, so a C/C++ directive's `src` (`tests/foo_test.cpp::TestName`) can
essentially never land in `tests.node_ids` even when the test genuinely exists
and ran. Retiring the structural fallback for C/C++ today would silently drop
ALL existing C/C++ TEST001-004 credit in any project using this gate, not
tighten it.

Real fix needs either (a) a ctest source-file mapping (e.g. parsing
`CTestTestfile.cmake` or `--show-only=json-v1`'s richer `properties` for a
`FIXTURES_SETUP`/source hint, if ctest exposes one) or (b) a different collector
for gtest-discovered cases via `--gtest_list_tests` per test binary, which does
carry real per-case names closer to source. Scoped out of T-0730 deliberately,
not silently dropped -- see T-0730's Done report.