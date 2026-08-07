## Done report

ROUTE CHOSEN: neither candidate route as originally conceived. Investigated
both against a real CMake 3.22.1 + ctest 3.22.1 toolchain (present on this
box) using minimal fixtures under /tmp scratch (transcripts below):

(a) `ctest --show-only=json-v1`: its own `backtrace` field resolves to the
    CMake SCRIPT location of the `add_test()` (or `gtest_discover_tests()`)
    call -- in every fixture tried, that is `CMakeLists.txt` line 5, never
    the real `.cpp` test source. This holds regardless of CMake version
    guarantees (the field itself is present since CMake 3.14, but it never
    points at the compiled source, only the invoking cmake script) -- route
    (a) as literally described in the ticket cannot answer source-accuracy
    at all, on any version.

(b) `--gtest_list_tests` on the binary: this box has no gtest installed
    (verified: no libgtest*, no gtest headers, no pkg-config entry) so a
    real gtest binary could not be built to test this directly; more
    fundamentally, `--gtest_list_tests`'s own output format carries only
    suite/case names, no file/line info, at any gtest version -- it cannot
    be source-accurate by itself either, confirmed by reading gtest's own
    list-tests output contract.

WHAT ACTUALLY WORKS (verified empirically, three real cmake+ctest runs +
one synthetic include()-file fixture, in /tmp scratch, not committed):
`CTestTestfile.cmake` (the file ctest itself reads) literally spells out
each test's executable path via `add_test(<name> "<path>")` -- both the
positional and `NAME`/`COMMAND` keyword `add_test()` spellings normalize
to this same shape. Cross-referencing that executable's cmake TARGET NAME
(parsed via `Path(command).stem`) against `compile_commands.json`
(`CMAKE_EXPORT_COMPILE_COMMANDS=ON`) gives the target's real compiled
source file(s). When a target compiles from exactly ONE source file (the
common case for a dedicated test binary, including every gtest case
`gtest_discover_tests()` registers against it, since that macro's
generated per-case `add_test()` calls all point at the same one binary) --
the mapping is exact and unambiguous: that source file IS the test's real
location.

Empirical verification (all four scenarios, real cmake 3.22.1 configure +
real ctest invocation, or a synthetic CTestTestfile.cmake/compile_commands.json
pair matching exactly what a real configure produces):
1. Single-source target, CMAKE_EXPORT_COMPILE_COMMANDS=ON: node id
   `src/widget_test.cpp::widget_adds` -- source-accurate, no fallback.
2. Two-source target (widget_test.cpp + helper.cpp): correctly refuses to
   guess, falls back to `build::widget_adds` with a logged FALLBACK
   warning naming the count.
3. No compile_commands.json at all (the common case: most projects never
   turn that cmake option on): falls back the same way, loudly, no crash.
4. gtest_discover_tests()-shaped CTestTestfile.cmake (include()s a sibling
   generated file with two dotted `Suite.Case` add_test() entries pointing
   at one binary, one compile_commands.json source): both cases correctly
   resolved to `src/widget_gtest.cpp::WidgetSuite::AddsOne` /
   `::AddsTwo` -- proving the include()-following and the dot-to-`::`
   name normalization (mirroring `frob.gates._symref_to_nodeid`'s own
   transform on the directive side) both work.

IMPLEMENTATION: `collect_cpp_tests` (src/frob/testing/_collect.py) gained
`_parse_ctest_command_map` (name -> executable path, scanning
CTestTestfile.cmake + one level of include()), `_cpp_target_sources`
(target name -> compiled source file set, from compile_commands.json),
`_cpp_test_source` (the ambiguity-refusing single-source lookup), and
`_cpp_node_id` (dot normalization). `_ctest_content_key`'s cache key now
also hashes compile_commands.json so a source-mapping-relevant change
(not just a test-set change) invalidates the cache.

RETIREMENT: `frob.gates._edge_has_execution_evidence` needed NO code
change -- its existing node-id check (real collected evidence) already
runs BEFORE the c/cpp structural fallback (`_edge_is_native_unverified`),
so the moment `collect_cpp_tests` emits an accurate `path::name` id for a
given edge, that edge is credited as genuine execution evidence and never
reaches the structural-fallback branch at all -- the fallback retires
itself per-edge automatically. `_NATIVE_TEST_EXTENSIONS` still lists
c/cpp extensions deliberately: most C/C++ `frob:tests` edges have no
configured build directory (or an ambiguous/multi-source one) at
gate-check time and still need the structural fallback's weaker credit;
only its explanatory comment was updated to describe the new reality (was
already updated in the source diff).

COVERAGE GAINED vs FALLBACK-RETAINED CASES:
- Gained: any c/cpp test whose binary is a single-source-file target and
  whose project was configured with CMAKE_EXPORT_COMPILE_COMMANDS=ON
  (covers the common "one .cpp file = one test binary" pattern directly,
  plus every gtest case gtest_discover_tests() registers against such a
  binary -- file-level granularity, which is exactly what a `frob:tests`
  `path::name` symref needs).
- Still on the structural fallback: no configured build directory at all
  (the common case when frob check runs without a prior cmake configure
  step); a configured build with no compile_commands.json; a
  multi-source-file test binary (refuses to guess which file "owns" the
  test).

Existing tests/test_testing.py::TestCollectCppTests (out of this ticket's
scope) all still pass unmodified -- its fixture's CTestTestfile.cmake uses
an UNQUOTED add_test() command, which the new command-map regex (which
requires a quoted path, matching every real cmake-generated
CTestTestfile.cmake this ticket's own real-toolchain runs produced) does
not match, so it degrades to the old build-dir id exactly as before; no
compile_commands.json is present in that fixture either. No regression.

### Changed
```
 src/frob/gates/__init__.py   |  30 ++-
 src/frob/testing/_collect.py | 217 ++++++++++++++++--
 tests/test_gates.py          | 204 ++++++++++++++++-
 tickets.md                   | 522 ++++++++++++++++++++++++++++++++++++++++++-
 4 files changed, 941 insertions(+), 32 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCppSourceAccurateCollection::test_single_source_target_is_source_accurate` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCppSourceAccurateCollection::test_multi_source_target_falls_back_loudly` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCppSourceAccurateCollection::test_no_compile_commands_falls_back_loudly` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCppSourceAccurateCollection::test_gtest_discover_tests_include_and_dot_names` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 11 error(s), 17288 warning(s), 356 waived
- error-findings: AFFECT001@src/frob/testing/_collect.py, ARCH001@src/frob/testing/_collect.py, COV001@src/frob/arch/_models.py, COV001@src/frob/gitlog/__init__.py, COV001@src/frob/process/parsers/common.py, COV001@src/frob/render/_color.py, COV001@src/frob/render/_elements.py, COV003@tickets/T-0639, COV003@tickets/T-0666, PERF003@src/frob/arch/_cpp_mayraise.py, PERF004@src/frob/arch/_cpp_mayraise.py
