## Done report

Root-caused by direct reproduction, NOT the hypothesis in the ticket
brief. Traced `frob.lang._extract`'s comment/symbol binding directly
(both via raw tree-sitter parse and via `extract()`): a
`# frob:tests` comment above `@pytest.mark.parametrize(...)` resolves
`following` correctly to the decorated function in every case tried
(single decorator, multi-line decorator call, decorator inside a test
class) -- `_effective_node` in `_walk_python.py` already returns the
`decorated_definition` node (spanning from the first decorator) as the
symbol's `sig_node`, so the binding was never actually broken.

Reproduced the REAL failure by copying feldspar into a scratch dir and
running `frob check --only gates` cold: the collected
`collect_python_tests` node id for a parametrized test is always
`path::func[case-id]` (one per parametrize case) -- `pytest
--collect-only` never emits the bare `path::func` id for a
parametrized test. `_valid_edges`'s (and `_pair_covered`'s) exact
`_symref_to_nodeid(e.src) in tests.node_ids` membership check can
therefore never validate a directive whose src resolves to the bare,
unparametrized symref -- which is exactly and only what a directive
placed above ANY parametrized test produces, regardless of comment
placement. A directive above a plain `def` "worked" only because a
non-parametrized test's collected id has no bracket suffix, so the
bare symref matches it exactly by coincidence -- there was never a
decorator-attachment bug, only a suffix-matching gap.

Fix: added `_node_id_collected(base_node_id, node_ids)` to
`src/frob/gates/__init__.py` -- true if `base_node_id` is collected
verbatim OR any collected id starts with `f"{base_node_id}["`. Used in
place of the exact membership check in both `_valid_edges` (TEST001/
TEST002/TEST003/TEST004 evidence validation) and `_pair_covered`
(TEST007).

Tests added (`tests/test_gates.py`):
`test_test003_satisfied_by_parametrized_test_node_id` (end-to-end
through `test_gate`: a `frob:tests ... kind="integration"` directive
above a parametrized test, `CollectedTests` populated with only the
bracketed per-case ids exactly as pytest would emit them, TEST003 must
NOT fire) and `test_node_id_collected_direct` (direct unit coverage:
verbatim match, parametrized-suffix match, no match, and a
bare-prefix-collision negative case -- `test_dens` must not
false-positive against `test_density[...]`).

Verified against the real bug: reproduced the failure first in a
scratch copy of `/home/logan/projects/feldspar`
(`tests/unit/test_library_thermo.py`, comment moved from the
workaround anchor test onto
`test_density_matches_reference_state_point`'s decorator) with the
PRE-fix global `frob` binary -- confirmed `TEST003` still fired for
`python/feldspar/thermo`; re-ran after this fix landed and `uv tool
upgrade frob` -- confirmed clean (no `python/feldspar/thermo` TEST003
line). feldspar itself was never edited, only a scratch rsync copy
under this session's scratchpad dir.

All 2 new tests pass; full repo suite `uv run pytest tests/ -q -n
auto` green after the change.

Same concurrent-repo-clobber incident as T-0274 hit this ticket's
first implementation pass too (uncommitted edits to
`src/frob/gates/__init__.py`/`tests/test_gates.py` were wiped between
tool calls) -- redone and committed immediately, same as T-0274.
