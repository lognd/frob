## Done report

Mirrors T-0610's PythonAdapter structure over tree-sitter-typescript, in
its own module `src/frob/arch/_typescript.py` mirroring `_python.py`'s
placement relative to `_normalized.py` exactly (REVIEWER CORRECTION,
round 2: the first submission put `TypeScriptAdapter` and its helpers
directly in `_normalized.py`, which is a design violation -- T-0609's
`_normalized.py` is a pure, tree_sitter-free model module by design, and
that placement hard-imported `tree_sitter` there while leaving the
protocol docstring's "typed `object` here to keep this module import-free
of `tree_sitter`" claim false. Moved out; `_normalized.py` is verified
tree_sitter-free again -- `ast.walk` over its imports shows only
`__future__`/`typing`/`pydantic`, and the protocol docstring's claim is
true again). `frob.arch._python` already proves this placement has no
circular-import problem: it imports `tree_sitter` + `frob.lang` +
`frob.arch._normalized` together with no cycle; `_typescript.py` mirrors
that exact import shape.

`TypeScriptAdapter` maps: `class_declaration` (extends/implements ->
`bases`, `public_field_definition` -> fields, `method_definition`
(including `constructor`) -> methods), `function_declaration`, a
top-level `const x = (...) => ...` arrow function bound to its name,
`override_modifier` -> `NormalizedFunction.overrides` (a real signal in
TS, unlike python which has none), branches (`if_statement`, boolean
`&&`/`||` `binary_expression`, `ternary_expression`), loops
(`for_statement`, `for_in_statement` for both for-of/for-in), calls
(`call_expression`), `this.x` field accesses, `return_statement`,
`throw_statement` -> raises, `catch_clause` -> catches, and every
`import_statement` clause shape (named/default/namespace/side-effect-only).
`max_nesting_depth`/`cyclomatic` mirror `_py_max_nesting`/`_py_cyclomatic`'s
semantics against TS's own grammar node types.

Not mapped (no `NormalizedModule` entity exists for these -- filed
T-0681 (ex-draft, id lost at land), a follow-up ticket, since adding a new entity kind is a
model change outside this adapter's own scope): `interface_declaration`,
`type_alias_declaration`, `enum_declaration`, and TSX JSX syntax.

Verified against real tree-sitter-typescript parses of hand-built `.ts`
snippets (no shared `tests/fixtures` dir exists for TypeScript yet, so
`TestTypeScriptAdapter` writes small `.ts` files under `tmp_path`,
mirroring `TestPythonAdapter`'s use of `tests/fixtures/arch_python`), one
test per entity kind (imports, class bases/fields, function
params/return-type, arrow function, branches/loops/calls/field-accesses,
for-of/for-in + ternary, throw/catch, override modifier,
constructor-as-method, export-wrapped declarations) plus a stays-sane
test combining everything in one realistic snippet (round-trips through
pydantic (de)serialization too, same as T-0609's hand-built shape test).
Imports updated to `from frob.arch._typescript import TypeScriptAdapter`
throughout `tests/unit/test_arch.py`; `frob:doc`/`frob:tests` directives
moved with the code and still point at the same
`tests/unit/test_arch.py::TestTypeScriptAdapter.
test_adapt_stays_sane_on_realistic_snippet` node id (unchanged by the
move).

`TestSharedCheckOnPythonAndTypeScript` proves the ticket's acceptance
criterion directly: `frob.arch._python`'s already-migrated (T-0610)
`_iter_normalized_functions`/`_normalized_is_complex` helpers -- pure
`NormalizedModule`/`NormalizedFunction` functions with no per-language
branch -- fire identically on an equivalent long/deeply-nested python
fixture (via `PythonAdapter`) and TypeScript fixture (via
`TypeScriptAdapter`), unmodified.

Gate/version bookkeeping: REL001 fired twice -- once (minor) for the new
public API when it briefly lived in `_normalized.py`, and again (major,
0.86.0 -> 0.87.0) after this round's move, since moving a public symbol to
a new module is itself a breaking change to its import path; both times
resolved with a version bump + `frob release stamp`. Scope was extended
via `frob ticket scope --add src/frob/arch/_typescript.py` (plus the
earlier `pyproject.toml`/`.frob-release.json`/`uv.lock` grant) for this.
Mid-ticket `git merge main` (round 1) picked up main's own advance to
0.86.0 (T-0573's release) while this ticket was in flight; resolved by
keeping main's higher version and re-running `frob release stamp` against
the merged tree, per the T-0431 conflict precedent.

### Changed
```
 .frob-release.json           |   2 +
 src/frob/arch/_normalized.py | 540 ++++++++++++++++++++++++++++++++++++++++++-
 tests/unit/test_arch.py      | 351 ++++++++++++++++++++++++++++
 tickets.md                   | 136 ++++++++++-
 4 files changed, 1025 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestTypeScriptAdapter::test_is_a_language_adapter` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_imports` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_class_bases_and_fields` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_function_params_and_return_type` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_arrow_function_bound_to_const` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_branches_loops_calls_field_accesses` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_for_of_and_ternary` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_raise_and_catch` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_override_modifier` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_constructor_is_a_method` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_export_wrapped_declarations` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_stays_sane_on_realistic_snippet` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSharedCheckOnPythonAndTypeScript::test_long_complex_function_flags_identically_across_languages` (pytest node id, verified passing when recorded)
