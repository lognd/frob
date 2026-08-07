## Done report

## Done report

Consumer inventory (grepped exhaustively for `split("::", 1)` applied to
closure()/CallGraph.calls-derived entries, not to Edge.src/Edge.target
which come from the graph snapshot and are always real symrefs):

- src/frob/gates/__init__.py `_cov006_third_file_reachable` (~line 3511-3524):
  iterates `reached_helpers = closure(test_only_graph, edge.src, ...)` and
  did `helper_symref.split("::", 1)[1]` unconditionally -- the confirmed
  IndexError site from the T-0809 reviewer note. Fixed: guarded with the
  new `_is_symref` helper, non-symref entries are skipped.
- src/frob/dup/_pipeline.py `_callee_name_map` (~line 617-628): iterates
  `graph.calls.get(caller_symref, ())` and did
  `callee_symref.split("::", 1)[1].rsplit(".", 1)[-1]` unconditionally.
  Fixed the same way with a matching `_is_symref` helper local to this
  file. `_callee_tokens` and `_splice_call_site` (which also split a
  `callee_symref`) only ever receive values sourced from
  `_callee_name_map`'s output, so filtering there protects them
  transitively -- no separate crash site to hardn independently.

Deviation from the T-0809 reviewer's estimate ("3 gates call sites +
dup/_pipeline"): I grepped every `split("::", 1)` in both files and
checked which operand is a closure()/graph.calls-derived value versus an
`Edge.src`/`Edge.target` (always real, DB-backed symrefs, safe to split
unconditionally) or an already-guarded value (`"::" in x else x`, lines
3008/3099). The other five `closure(...)` call sites in gates.py
(`_cov006_public_wrapper_reachable`, `_cov006_implicit_dispatch_reachable`,
`_cov006_edge_violation`, and the second closure call inside
`_cov006_implicit_dispatch_reachable`) only ever use the closure result in
an `x in closure(...)` MEMBERSHIP test, which cannot raise on an odd
string -- a sentinel simply fails to match, no crash, no fix needed there.
I found exactly one real crash site per file (gates.py, dup/_pipeline.py),
not three in gates.py; disclosing this rather than inventing hardening
for sites that were never actually vulnerable.

No shared single home for `_is_symref`: the natural home is
`frob/graph/callgraph.py` (where `UNRESOLVED_CALLEE` and `closure()` are
defined), but that file is outside T-0814's declared scope
(`src/frob/gates/__init__.py`, `src/frob/dup/_pipeline.py`,
`tests/test_gates.py`). Each file keeps its own one-line
`_is_symref(entry: str) -> bool: return "::" in entry` predicate with a
matching docstring instead -- filed no new ticket for the consolidation
since it is a one-line, zero-behavior-risk duplication, not worth its own
ticket overhead, and disclosing it here per playbook's "disclose cuts
honestly" is what governs it.

Changed:
- src/frob/gates/__init__.py::_is_symref (new)
- src/frob/gates/__init__.py::_cov006_third_file_reachable (hardened loop)
- src/frob/dup/_pipeline.py::_is_symref (new)
- src/frob/dup/_pipeline.py::_callee_name_map (hardened loop)
- tests/test_gates.py: 4 new regression tests

Evidence (measured, `uv run --frozen pytest tests/test_gates.py
tests/test_dup*.py`): 459 passed in 11.62s (re-verified after ruff
reformat: 459 passed in 11.98s). New node ids, all collected and passing:
- tests/test_gates.py::TestCoverageGate::test_is_symref_gates
- tests/test_gates.py::TestCoverageGate::test_cov006_third_file_reachable_skips_unresolved_callee_sentinel
- tests/test_gates.py::TestDupPipelineClosureConsumers::test_is_symref_dup
- tests/test_gates.py::TestDupPipelineClosureConsumers::test_callee_name_map_skips_unresolved_callee_sentinel

Real symref behavior unchanged: the existing COV006/dup suites (459 tests
total across both files) stay green with no modifications to any
pre-existing test.

Filed: none (see the `_is_symref` duplication note above -- disclosed
rather than filed, one-line predicate, zero behavior risk).

Gates: `uv run --frozen frob check --ticket T-0814 --only <stage>`
chunked over all 5 stage groups (lint, static, gates-fast, gates-native,
gates-security) after `frob ticket sweep T-0814` re-ran the pre-work
sweep post-edit -- all 5 groups PASS, 0 new errors (only pre-existing,
already-waived warnings across the whole repo). `git diff main
--diff-filter=D --stat` is empty.

Worktree: /home/logan/projects/frob/.claude/worktrees/agent-ac7b7a66bce3bea1b

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)
