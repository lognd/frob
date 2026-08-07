## Done report

Changed:
- src/frob/graph/callgraph.py::_resolve_edges (split into a data-extraction
  phase + `_resolve_edges_python`; native dispatch prototyped, disclosed as
  measured-slower, reverted to unconditional pure-Python)
- src/frob/graph/callgraph.py::_called_names, ::_ordered_called_names,
  ::_referenced_names, ::_unresolved_exempt_names (docstrings updated with
  T-0930 disclosure of the prototyped-and-reverted native path; bodies
  unchanged from pre-T-0930)
- src/frob/graph/_core.py (new file: `core_available`, `resolve_call_edges_native`
  -- the one kernel actually available for a future batched caller)
- frob-core/src/lib.rs::resolve_call_edges, ::called_names,
  ::ordered_called_names, ::referenced_names, ::unresolved_exempt_names,
  ::scan_call_tokens, ::is_identifier_token (new Rust kernels + 8 new unit
  tests, all passing; parked, not wired to any Python caller by default)
- frob-core/frob_core.pyi (type stub for the 5 new exported functions)
- tests/test_graph.py::TestResolveCallEdgesNative (2 golden parity tests:
  `resolve_call_edges_native` vs `_resolve_edges_python` over both a real
  `src/frob/gates` package and a synthetic edge case; PLUS a 3rd test,
  `test_core_available_true_dispatches_to_native_spy_and_false_does_not`,
  added post-review to pin `core_available()`'s True/False dispatch
  decision observably both ways via a `sys.modules["frob_core"]` spy --
  the golden-parity tests above `pytest.skip()` when `frob_core` isn't
  built and therefore never fail on a mutated `core_available`; the new
  test does not depend on the real extension at all, so it can't
  vacuously skip)
- docs/audits/check-performance.md (T-0930 remediation log appended)
- docs/modules/graph.md (new "Rust core" section)
- docs/modules/dup.md (kernel list + prose updated: 5 new pyfunctions
  registered in the same `frob_core` pymodule)

Evidence:
- `tests/test_graph.py::TestResolveCallEdgesNative::test_native_matches_python_fallback_on_a_real_package`
- `tests/test_graph.py::TestResolveCallEdgesNative::test_native_matches_python_fallback_on_a_synthetic_edge_case`
- `tests/test_graph.py::TestResolveCallEdgesNative::test_core_available_true_dispatches_to_native_spy_and_false_does_not`
  (all 3 bound as ticket evidence)
- `frob-core/src/lib.rs`'s 8 new `mod tests` cases (called_names/ordered_called_names/
  referenced_names/unresolved_exempt_names/resolve_call_edges x3), `cargo test`
  clean (46 total tests pass)
- `frob test --base main`: python touched-set (8 outcomes) exit=0, rust
  touched-set (2 cases) exit=0
- Full `tests/test_graph.py` (118 tests) and `tests/test_gates.py` DeadSymbol/
  Protocol/CallGraph/ReferenceGraph subsets: all pass unchanged

Mutation kills hand-verified (T-0930's TEST016 follow-up, both surviving
mutants at `src/frob/graph/_core.py:42-43`, `core_available`'s
`return False`/`return True`):
- Mutant A (`return False` on the `except ImportError` branch mutated to
  `return True`): forced `sys.modules["frob_core"] = None` (real
  ImportError), asserted `core_available() is False` -- new test FAILED
  with `AssertionError: assert True is False`. Confirmed kill.
- Mutant B (`return True` on the success branch mutated to `return
  False`): injected a fake importable module into
  `sys.modules["frob_core"]`, asserted `core_available() is True` --
  new test FAILED with `AssertionError: assert False is True`. Confirmed
  kill.
- Reverted both mutants; `git diff src/frob/graph/_core.py` empty
  (byte-identical to pre-mutation); full `tests/test_graph.py` (118
  tests) re-run clean afterward.
- `frob ticket close T-0930 --evidence ... (3 ids)` re-run: no TEST016
  warning this time (previously fired with the 2-evidence set killing
  0/2 mutants); ticket was already `done` from the prior close so this
  re-run hit `InvalidTransition: done -> done` (expected, harmless --
  evidence recording happens before the transition check and succeeded,
  confirmed by the CLI's own "evidence now has 3 id(s)" message and the
  absence of the TEST016 warning).

Rows migrated: NONE shipped as an active native path (see disposition below) --
row 8 (`dead_symbols`) was investigated to completion, with a genuine,
honest negative result.

Benchmark (see docs/audits/check-performance.md's T-0930 remediation log
for full detail): `dead_symbol_gate` called directly, `run_memo_scope()` +
pre-warmed `build_graph` so `parse_file`'s memo is hot for both arms,
`time.thread_time()`, median of 7 runs over this repo's own `src/frob/gates`
package (46 sub-packages).

```
_resolve_edges (batched, 46 calls):        native 0.164s vs python 0.127s (native ~29% SLOWER)
token-scan helpers (per-symbol, ~13.6k calls): native 0.242s vs python 0.135s (native ~79% SLOWER)
```

PyO3's per-call marshaling cost (Python containers -> Rust and back)
exceeds the matching/scan loop's own already-small pure-Python cost at
this repo's real per-package/per-symbol data scale. All 5 kernels were
therefore built, tested, and then DELIBERATELY left unwired -- shipping
them as the default path would make `frob check` slower for anyone with
`frob_core` built, which is the opposite of this ticket's goal.

Rows deferred, children filed:
- `static` bucket (row 1): `dup`'s share is already native
  (pre-existing `frob.dup._core`); `cycle`/`arch`/`bind`/`exports` not
  investigated. Filed T-0950 to size `frob.cycle`'s Tarjan SCC
  (clean data-in/data-out shape, same class this ticket looked for) against
  real repo-scale import graphs before porting.
- `archgate` (row 3) and `pii_structural` (row 7): read-level investigated
  only. Both are dominated by tree-sitter `Node`/AST-shaped semantic
  analysis, not frob_core's compute-only data-in/data-out convention, without
  a much larger parser-equivalence investment this ticket did not size.
  Filed T-0951 to determine feasibility or dispose honestly.

Gates: `frob check --ticket T-0930` (chunked: lint, static, gates-native,
gates-security, gates-fast, plus a full unchunked `--ticket T-0930` pass)
all clean, 0 errors. Two pre-existing `ruff-format` warnings on
`src/frob/arch/_lock_ordering.py`/`tests/unit/test_arch.py` predate this
ticket (documented as pre-existing in T-0928/T-0929's own Done reports),
not touched, not waived under this ticket.

### Changed
```
 docs/audits/check-performance.md | 119 ++++++++++++++
 docs/modules/dup.md              |  15 ++
 docs/modules/graph.md            |  37 +++++
 frob-core/frob_core.pyi          |  16 ++
 frob-core/src/lib.rs             | 326 +++++++++++++++++++++++++++++++++++++++
 src/frob/graph/_core.py          |  94 +++++++++++
 src/frob/graph/callgraph.py      | 146 ++++++++++++++----
 tests/test_graph.py              | 109 +++++++++++++
 tickets.md                       | 260 ++++++++++++++++++++++++++++++-
 9 files changed, 1087 insertions(+), 35 deletions(-)
```

### Evidence
- `tests/test_graph.py::TestResolveCallEdgesNative::test_native_matches_python_fallback_on_a_real_package` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestResolveCallEdgesNative::test_native_matches_python_fallback_on_a_synthetic_edge_case` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestResolveCallEdgesNative::test_core_available_true_dispatches_to_native_spy_and_false_does_not` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
