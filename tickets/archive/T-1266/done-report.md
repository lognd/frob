## Done report

Investigation (before writing any test): the ticket's own description
already quotes the exact reason no source change is needed for
acceptance[0] -- T-0886 (landed earlier, tickets-archive.md) already
built `collect_cpp_tests` to cross-reference each ctest test's executable
against `compile_commands.json` (`_cpp_target_sources`/`_cpp_test_source`
in src/frob/testing/_collect_cpp.py) and upgrade to a real
`<source>::<name>` node id whenever the target compiles from exactly one
source file. `_edge_has_execution_evidence` in src/frob/gates/__init__.py
already checks real collected node ids (`_node_id_collected`/
`_symref_to_nodeid`) BEFORE falling through to the c/cpp structural
fallback (`_edge_is_native_unverified`) -- so an unambiguous single-source
c/cpp `frob:tests` edge already resolves against real evidence today, no
change needed in src/frob/gates/__init__.py or src/frob/testing/
_collect.py. Verified this is not merely asserted in a docstring:
tests/test_gates.py::TestCppSourceAccurateCollection (T-0886) already
proves collect_cpp_tests itself produces the right node-id shape for the
single-source case, and tests/test_gates.py::TestTest013NativeUnverified
(T-0552) already proves the disclosed-unverified TEST013 signal fires for
the genuinely-unresolved case (acceptance[1]).

What WAS missing, and what I added: no existing test proved the GATE-LEVEL
integration for c/cpp specifically -- that a real `frob:tests` edge in the
graph actually takes `_edge_has_execution_evidence`'s real-node-id branch
for a c/cpp symbol, the same way
`TestNativeTestCollectors::test_ts_directive_resolves_via_real_vitest_node_id`
already proves it for TS. Added
`test_cpp_directive_resolves_via_real_ctest_node_id` in
tests/test_gates.py (mirrors that TS test's shape exactly): a `.cpp` file
with a real `frob:tests` directive, `tests.node_ids` holding the exact
`<source>::<name>` shape `collect_cpp_tests` emits for an unambiguous
single-source ctest test, and asserts TEST001/002/013 all stay clean --
proving the edge resolves via real evidence, not the structural fallback.

No production code changed in src/frob/gates/__init__.py or
src/frob/testing/_collect.py -- the mechanism both acceptance criteria
describe already exists and already works; this ticket's contribution is
closing the missing test-evidence gap that left both acceptance criteria
UNBOUND despite the underlying behavior being correct.

Verified: `uv run pytest tests/test_gates.py -k "cpp or Cpp or
native_unverified or NativeTestCollectors" -q` -- 11 passed, including the
new test. `uv run frob check --ticket T-1266 --only docanchor --only
doclink --only lint --only test` -- 0 errors (pre-existing, unrelated ty/
ruff-format baseline noise only, matching every other ticket's captured
claims this session).

### Changed
```
 .github/workflows/ci.yml |  40 ++++++++++++-
 docs/modules/gates.md    |  39 +++++++++++++
 tests/test_gates.py      |  28 +++++++++
 tickets.md               | 148 ++++++++++++++++++++++++++++++++++++++++++++---
 4 files changed, 246 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestNativeTestCollectors::test_cpp_directive_resolves_via_real_ctest_node_id` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTest013NativeUnverified::test_fires_on_structural_only_edge` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 844 warning(s), 693 waived
- error-findings: none (measured, zero errors)
