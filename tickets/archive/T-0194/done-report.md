## Done report

Changed:
- frob-core/src/lib.rs::children_lists (new, private helper)
- frob-core/src/lib.rs::AntiUnifyErr (new, private enum)
- frob-core/src/lib.rs::Template (new, private struct)
- frob-core/src/lib.rs::anti_unify_walk (new, private recursive walk)
- frob-core/src/lib.rs::anti_unify_core (new, pure kernel, cargo-tested directly)
- frob-core/src/lib.rs::anti_unify (new, #[pyfunction], registered in frob_core pymodule)
- src/frob/dup/_core.py::anti_unify (new Python shim, Result-returning)
- src/frob/dup/_models.py::AntiUnifyTemplate (new frozen pydantic model)
- src/frob/dup/_models.py::DupError.HoleCeilingExceeded (new error variant)
- src/frob/dup/__init__.py (anti_unify, AntiUnifyTemplate re-exported)
- docs/modules/dup.md (new "Anti-unification (Plotkin lgg)" section,
  frob-core kernels bullet list, DupError/AntiUnifyTemplate in the
  Public API code block, frob:describes directives)
- CHANGELOG.md (new [0.10.0] entry), pyproject.toml (version 0.9.0 ->
  0.10.0), .frob-release.json (re-stamped)
- tests/unit/test_dup_core.py (TestAntiUnify class, registration-list
  and core-unavailable-path coverage)

Kernel API: `anti_unify_core(labels_a, parents_a, labels_b, parents_b) ->
Result<Template, AntiUnifyErr>` is the pure, PyO3-independent algorithm
(cargo-testable in isolation); `Template { labels, parents, bindings_a:
Vec<(hole_id, a_index)>, bindings_b: Vec<(hole_id, b_index)> }`. The
`#[pyfunction] anti_unify` wrapper never raises across the FFI boundary
(matching every other kernel in this crate) -- it returns `(ok: bool,
template_labels, template_parents, bindings_a, bindings_b)`, all-empty
when `ok == false`. The Python shim (`frob.dup._core.anti_unify`) turns
that into `Result[AntiUnifyTemplate, DupError]`, with
`Err(DupError.HoleCeilingExceeded)` on `ok == false`.

Algorithm: lockstep top-down recursive walk (`anti_unify_walk`) over the
same node-array representation `apted_similarity` consumes. At each
`(a, b)` position: label AND arity match -> emit the shared node, recurse
pairwise into children in source order; otherwise -> emit `$hole_N`
(N = preorder emission order, hence deterministic), bind `(N, a)` to
`bindings_a` and `(N, b)` to `bindings_b`, do not recurse. HOLE-CEILING
sanity: hole_count * 2 > total_node_count -> `Err(HoleCeilingExceeded)`.
Both-empty inputs -> Ok(empty template, 0 holes); exactly-one-empty ->
always exceeds the ceiling.

Cargo tests (frob-core, run via
`PYO3_PYTHON=<worktree>/.venv/bin/python
LD_LIBRARY_PATH=<uv-python-install>/lib cargo test`, per the worktree
natives note): 30 passed, 0 failed, including
`anti_unify_identical_trees_has_zero_holes`,
`anti_unify_single_leaf_divergence_binds_one_hole`,
`anti_unify_arity_mismatch_becomes_a_hole_not_a_crash`,
`anti_unify_wildly_different_trees_exceeds_hole_ceiling` (the
hole-ceiling sanity test the ticket names),
`anti_unify_empty_vs_empty_is_empty_template`,
`anti_unify_deterministic_hole_numbering`,
`anti_unify_pyfunction_wraps_hole_ceiling_as_false_sentinel`.

Python (`uv run pytest tests/unit/test_dup_core.py -q`): 25 passed
(TestAntiUnify's 5 new cases plus every pre-existing `_core` shim test,
including `test_frob_core_module_registers_exported_kernels` updated to
assert `anti_unify` is registered, and
`test_core_unavailable_path_is_err_not_exception` extended for
`anti_unify`).

`uv run pytest --collect-only -q`: clean, no collection errors (make
core ran first, per the worktree natives note).

Gates: `uv run frob check --ticket T-0194` (after extending scope, above,
and `frob ticket sweep T-0194` to refresh the pre-work stamp) -> 2 errors,
both pre-existing COV003 findings on ticket T-0214 (unrelated; confirmed
via `git stash` + `frob check --ticket T-0194` on the pre-change tree,
which already showed the same 2 T-0214 COV003 errors). REL001 (new public
surface: `anti_unify`, `AntiUnifyTemplate`, `DupError.HoleCeilingExceeded`)
resolved by bumping pyproject.toml 0.9.0 -> 0.10.0, a new [0.10.0]
CHANGELOG.md entry, and `frob release stamp`. `ruff check`/`ruff format
--check` clean under both the PATH binary and `.venv/bin/python -m ruff`
(the project-pinned version). `ty check src/frob/dup/` clean.
`cargo fmt --check` shows only pre-existing drift on lines this ticket
did not touch (confirmed via `git stash` on the same command); the one
line this ticket added that fmt would reformat was fixed by hand.
`cargo clippy --all-targets` (via the same PYO3_PYTHON/LD_LIBRARY_PATH):
no errors, only pre-existing warning categories already present
elsewhere in the file (needless_range_loop, too_many_arguments,
type_complexity -- none new to this ticket's logic beyond one
type_complexity note on the tuple return, left as-is to match the
crate's existing FFI-boundary tuple-return convention).
`uv run frob test --base main`: python exit=0 (3.26s), rust exit=0
(0.08s), both selected via the touched-set (`tests/unit/test_dup.py`,
`tests/unit/test_dup_core.py`, and the five new
`anti_unify_*` cargo tests by name).
`git diff main --diff-filter=D --stat`: empty (no unintended deletions).
`frob-core/Cargo.lock`: no diff (no churn). `uv.lock`: one line, the
version bump reflection, not churn.

Filed: none (no out-of-scope work found; T-0195/T-0287 already exist and
are the intended downstream consumers per the ticket's own description).
Scope extended (not filed as a separate ticket) to add
docs/modules/dup.md, pyproject.toml, CHANGELOG.md, uv.lock, and
.frob-release.json -- all direct, unavoidable consequences of this
ticket's own new public API (REL001's version-bump/changelog demand,
COV001's doc-edge convention for new public symbols), not unrelated work.

Not closing per the agent playbook (review-gated flow) -- left `queued`
transitioned to `in-progress` by `frob ticket start`; reviewer closes.
