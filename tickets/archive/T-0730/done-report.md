## Done report

## Done report

Changed:
- src/frob/gates/__init__.py::_load_tests (now calls collect_ts_tests/collect_cpp_tests too, merging into one CollectedTests)
- src/frob/gates/__init__.py::_NATIVE_TEST_EXTENSIONS (`.ts`/`.tsx` removed -- retired structural fallback for TS)
- src/frob/gates/__init__.py (docstrings on _is_native_test_symref, _valid_edges, _edge_is_native_unverified, _case_count, _test013_native_unverified, test_gate, and the TEST013 rule comment updated to say "c/cpp" instead of "ts/c/cpp", disclosing why C/C++ could not retire in this pass)
- tests/test_gates.py::TestNativeTestCollectors (new: 4 tests)
- tests/test_gates.py::TestTest013NativeUnverified (docstring updated to note ts's retirement)

Evidence (all bound with --accepts 0):
- tests/test_gates.py::TestNativeTestCollectors::test_ts_directive_resolves_via_real_vitest_node_id
- tests/test_gates.py::TestNativeTestCollectors::test_ts_structural_only_edge_no_longer_credited
- tests/test_gates.py::TestNativeTestCollectors::test_ts_no_longer_in_native_extensions
- tests/test_gates.py::TestNativeTestCollectors::test_load_tests_merges_all_four_collectors

Measured: `uv run pytest tests/test_gates.py -p no:cacheprovider -q` -- full file green (7 batches of dots, no failures). `uv run pytest tests/test_gates.py -k "TestNativeTestCollectors or TestTest013NativeUnverified" -n0 -v` -- "6 passed".

Cut / disclosed gap: the ticket's title says "retire the ts/c/cpp structural fallback" but the acceptance criterion given only covers TS ("GIVEN a vitest project ... THEN ... the structural fallback no longer credits unverified ts edges"). C/C++ was deliberately NOT retired -- `collect_cpp_tests`'s own docstring discloses a KNOWN APPROXIMATION: a ctest node id anchors to the BUILD DIRECTORY (`<build_dir>::<test name>`), not the real source file a C/C++ `frob:tests` directive lives above, so a directive's `src` symref can essentially never land in `tests.node_ids` even for a real, passing test. Retiring the C/C++ fallback today would have silently dropped ALL existing C/C++ TEST001-004 credit rather than tighten it. Filed T-0886 ("gates: real ctest source-accurate collection so the cpp structural fallback can retire") to track the real fix (a source-mapping ctest collector or a gtest --gtest_list_tests-based collector).

Gates: `FROB_AGENT=1 FROB_WORKTREE=<worktree> uv run frob check --ticket T-0730 --only <stage>` clean (exit 0) for lint, static, gates-native, gates-security. `gates-fast` shows pre-existing errors (COV001/DOC002 on src/frob/exports/__init__.py from T-0858's own landed state, COV007 findings across unrelated files, DOC004 findings in docs/guides/install.md and docs/modules/testing.md) -- none touch src/frob/gates/__init__.py or tests/test_gates.py; confirmed via `grep` that zero COV/DOC/SCOPE/PRE findings in that run reference my files.

Filed: T-0886 (see above).

Scope: `git diff main --diff-filter=D --stat` is empty.

### Changed
```
 docs/modules/gates.md             |  38 +++++-
 src/frob/gates/__init__.py        | 123 ++++++++++++-------
 src/frob/gates/_pii_structural.py | 201 ++++++++++++++++++++++++++----
 tests/test_gates.py               | 249 +++++++++++++++++++++++++++++++++++++-
 tickets.md                        | 125 ++++++++++++++++++-
 5 files changed, 656 insertions(+), 80 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestNativeTestCollectors::test_ts_directive_resolves_via_real_vitest_node_id` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestNativeTestCollectors::test_ts_structural_only_edge_no_longer_credited` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestNativeTestCollectors::test_ts_no_longer_in_native_extensions` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestNativeTestCollectors::test_load_tests_merges_all_four_collectors` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
