## Done report

Before/after long-function counts (`uv run frob arch .` filtered per
subtree):

- src/frob/vet/**: 20 -> 0
- src/frob/tickets/**: 13 -> 0
- src/frob/check/**: 8 -> 0
- src/frob/__main__.py: 7 -> 0
- src/frob/deploy/**: 9 -> 0
- src/frob/fuzz/**: 6 -> 0
- src/frob/lang/**: 3 -> 0
- src/frob/testing/**: 4 -> 0

Total: 70 -> 0 (repo-wide `uv run frob arch .` full output separately
confirms zero `long-function` matches under any of the eight scoped
globs).

Method: extraction only (one cohesive, purpose-named `_leading_underscore`
helper per over-long function; a few functions were long only due to an
oversized historical-rationale docstring and were fixed by relocating
that prose to a leading `#` comment above the `def`, per the dispatch
instructions -- no documented invariant/guarantee text was dropped, only
relocated). No public top-level `def`/`class`/`__all__` entry changed.
No behavior change: every extracted helper receives/returns exactly what
the inline code used, preserving early-return order, short-circuit order,
Result/exception propagation, and mutate-vs-copy semantics.

Regressions caught and fixed during verification (not present in the
final diff):
- `_apply_renumber_mapping`/`_persist_renumber`/`_build_renumber_report`
  in `src/frob/tickets/__init__.py`: `int` vs `bool` typing mismatch from
  `_apply_renumber`'s real `int` return type -- fixed by typing the
  threaded parameters `int` throughout (ty-clean).
- `src/frob/testing/_collect.py`/`_runners.py`: new `_cargo_list_result`/
  `_runner_outcome` helpers were typed `Result[object, object]` /
  `tuple[str, ...]`, which ty's invariant-generics rule rejected against
  the real `Result[ProcResult, GitError]` / `list[str]` callers pass --
  fixed with the real types.
- `src/frob/fuzz/_arbitrary.py`: `_field_strategies_for`'s
  `Result[dict[str, Any], FuzzError]` was returned bare from
  `Result[object, FuzzError]`-typed callers -- fixed by re-wrapping the
  `Err` explicitly instead of returning the narrower Result object.
- `src/frob/fuzz/_signatures.py`: `_resolve_callable`/`_resolve_hints`/
  `_annotated_types_for_target` were typed `object` where
  `inspect.signature`/`typing.get_type_hints` need a callable -- fixed
  with `Callable[..., object]`.
- `src/frob/vet/_hook.py`: extracting the not-None check into
  `_unverified_lookup_verdict` broke ty's None-narrowing on
  `lookup.published_at` at the call site -- fixed with an explicit
  `assert lookup.published_at is not None` plus a comment explaining why.
- `src/frob/lang/_walk_strata.py`: `_check_declared_count_drift`'s
  `parsed_ok` parameter was typed `object` where `_declared_count` needs
  `dict` -- fixed with the real type.
- `src/frob/check/__init__.py`: `_cpp_post_build_tasks`'s narrower
  `Callable[[], ToolResult | None]` return type didn't match
  `_run_tasks_concurrently`'s `Callable[[], ToolResult | list[ToolResult]
  | None]` parameter (list invariance) -- fixed by widening the helper's
  return type to match.
- `src/frob/deploy/_conform.py`: `_deploy002_extras`/`_deploy003_misses`
  were typed to take `set[MutationTarget]` but callers pass the
  `frozenset[MutationTarget]` result of a set-difference -- fixed with
  the real type.
- Five `# frob:doc`/`# frob:invariant`/`# frob:tests` directive comments
  (on `scan_tree`, `build_containment_report`,
  `match_dependencies_against_mirror`, `renumber_one`, `transition`,
  `add_cmd_evidence`) were caught by an `Edit` that inserted a new helper
  function directly above the original `def`, leaving the directive
  attached to the wrong (private, non-obligated) function -- caught by
  `frob check`'s COV001 gate going from 0 to 6 errors, fixed by moving
  each directive back onto its original public function. This is the
  concrete reason the gate re-run (not just `frob arch`) matters as a
  verification step for this kind of mechanical extraction.

Verification:
- `uv run frob arch .` filtered to the eight scoped globs: 0
  `long-function` matches (was 70).
- `uv run ruff check` and `uv run ruff format --check` on every touched
  file: clean, under both the project-pinned `uv run ruff` (0.14.x) and
  the PATH `ruff` (0.14.10).
- `uv run ty check` on every touched file: 2 pre-existing diagnostics on
  `src/frob/vet/_allow.py:72-73` (`int(vet.get(...))` /
  `vet.get("registry_base_url")` against an `object`-typed dict value) --
  confirmed identical on `main` via `git show main:src/frob/vet/_allow.py`
  (same lines, untouched logic, only relocated into a helper function by
  this ticket); zero new ty diagnostics.
- `uv run pytest` on every touched-package test file (listed under
  `evidence:` above): all green, no skips beyond pre-existing ones.
- `make coverage` (full suite + branch coverage + `frob check
  --stamp-coverage`): green, 389 files stamped.
- `uv run frob check .` (full repo, post-coverage-stamp): `pass ruff-
  check`, `pass ruff-format`, `pass gates` (0 errors, 3 warnings, 221
  waived -- all 3 warnings and all waivers pre-exist, unrelated to this
  slice); `FAIL ty` is exactly the 2 pre-existing `_allow.py`
  diagnostics above (confirmed via diff against `main`, not introduced by
  this ticket).
- `git diff main --diff-filter=D --stat`: empty (no deletions outside
  scope).
- Cargo.lock: no churn (no Rust source touched by this ticket).
- No non-ASCII characters introduced.

Not closing this ticket -- leaving for the reviewer per the review-gated
workflow (playbook section 11).
