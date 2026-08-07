## Done report

Changed:
- src/frob/strata/_facts.py::build_facts (module-level `import strata_core`
  guarded with importlib + `ModuleType | None`, T-0133's pattern; fails
  closed on `StrataError.NativeExtensionUnavailable` before any lattice/id
  validation runs)
- src/frob/strata/_facts.py::FactBase.reachable /
  FactBase.worst_age / FactBase.propagated_demand (added
  `assert strata_core is not None` -- ty-visible proof that these can only
  run on a `FactBase` a successful `build_facts` already produced, so
  `strata_core` is present by construction; keeps `ty check` clean without
  re-guarding call sites that are unreachable with it absent)
- src/frob/strata/_parse.py::parse_module (same guarded-import pattern;
  the OTHER unguarded `import strata_core` found by grepping
  `src/frob/strata/` -- `_ast.py` and `_secrets.py` only mention
  `strata_core` in docstrings, no live import)
- src/frob/strata/_errors.py::StrataError.NativeExtensionUnavailable (new
  ErrorSet member both guarded sites return)
- src/frob/strata/_design_load.py::DEFAULT_DESIGN_DIR (reviewer follow-up:
  added a two-way doc cross-reference -- a comment pointing at
  `frob.gates._DEFAULT_DESIGN_DIR`'s deliberate mirror literal, plus
  naming the sync-lock test that pins them together -- so the constant's
  own docstring and the mirror's docstring point at each other rather
  than only one side knowing about the duplication)

Audit: `grep -rn "import strata_core\|strata_core\." src/frob/strata/`
found exactly two live imports (`_facts.py`, `_parse.py`); both guarded.
`_design_load.py::load_design_ids` already treats a `parse_module` Err as
a per-file `DesignLoadError` rather than propagating, so it degrades for
free once `_parse.py` stopped crashing.

Evidence:
- tests/unit/strata/test_facts.py::TestBuildFactsNativeExtensionUnavailable::test_build_facts_returns_native_extension_unavailable
- tests/unit/strata/test_parse.py::TestParseModuleNativeExtensionUnavailable::test_parse_module_returns_native_extension_unavailable
- Full suite (real numbers, `uv run pytest tests/test_gates.py
  tests/unit/strata/ tests/unit/test_lang_strata.py -q`): all green.
- `frob test --base main`: python exit=0.
- `uv run ty check`: All checks passed (the 3 `unresolved-attribute`
  diagnostics on `FactBase`'s closure methods, from narrowing
  `ModuleType | None`, are resolved by the `assert strata_core is not
  None` guards above).
- `uv run ruff format --check .`: 281 files already formatted.

Filed: none (the only other unguarded-import discovery, T-0136's surface-
grammar gap, was already filed before this ticket started and is out of
scope here).

Gates: `frob check --ticket T-0134` (re-run after honest re-scoping and
`frob ticket sweep T-0134`) is NOT clean end-to-end -- 4 errors, not 0:
one pre-existing `DOC001` (docs/guides/install.md, from T-0133's merge,
untouched here) plus THREE `SCOPE001` errors
(`.github/workflows/ci.yml`, `src/frob/gates/__init__.py`,
`tests/test_gates.py`). Cause: T-0134 and T-0135 are worked sequentially
in the SAME worktree with neither ticket committed, so T-0134's
scope-gate diff-scan sees T-0135's uncommitted files too and correctly
flags them as outside T-0134's now-honest, narrowly-corrected scope
(`src/frob/strata/_facts.py`, `_parse.py`, `_errors.py`,
`_design_load.py`, their two test files, and `tickets.md` -- no longer
the over-broad `src/frob/strata/**`/`tests/**` globs that previously
masked this). This is real cross-ticket file visibility, not a false
positive and not something either ticket's own diff caused; it resolves
itself once either ticket is committed/closed. All findings on T-0134's
own files remain zero-unwaived; the 22 waived findings and the COV002
informational entries (symbols covered by this ticket's or T-0135's own
open scope) are the only other output.
