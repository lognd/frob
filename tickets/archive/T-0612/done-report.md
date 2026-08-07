## Done report

Adds `frob.arch._rust.RustAdapter`, the third `LanguageAdapter` (T-0609)
implementation after T-0610's `PythonAdapter`/T-0611's `TypeScriptAdapter`,
mapping a `tree-sitter-rust` parse onto the shared `NormalizedModule` shape.
Kept in its own module `src/frob/arch/_rust.py` (never `_normalized.py`,
which stays a pure tree_sitter-free model module per T-0609's design, and
never `frob.lang._walk_rust.py`, which is the unrelated symbol-catalog
walker `frob check`'s doc/test coverage graph consumes) -- the exact
placement the T-0611 review corrected, applied here from the start; scope
was extended (`frob ticket scope --add src/frob/arch/_rust.py --reason
...`) to cover it since the ticket's original scope only listed
`src/frob/lang/_walk_rust.py`/`_normalized.py`/`tests/unit/test_arch.py`.

`RustAdapter` maps: `struct_item` (named/tuple/unit fields ->
`NormalizedField`, tuple fields get positional names "0"/"1"/...),
`enum_item` (each variant -> a `NormalizedField`, since no
`NormalizedVariant` entity exists -- filed T-0743 (ex-draft, id lost at land), a follow-up,
not folded into this ticket's own scope, same class of gap as T-0611's
TS interface/type-alias follow-up), `trait_item` (both a bodyless
`function_signature_item` and a defaulted `function_item` become the
trait's own `NormalizedClass` methods), `impl_item` (an inherent
`impl Type { ... }`'s methods attach to `Type`'s class; a trait impl
`impl Trait for Type { ... }`'s methods ALSO attach to `Type`, `Trait`'s
name is appended to `Type.bases`, and each such method's `overrides` is
set to its own name -- rust's closest analogue to an explicit override
signal, since a trait-impl method body IS the fulfillment of that
trait's contract even without a keyword), top-level `function_item`s,
branches (`if_expression`, boolean `&&`/`||`, and -- UNLIKE
`_python.py`'s deliberate exclusion of match/case from its cyclomatic
proxy -- each individual `match_arm` counted as its own branch, per this
ticket's explicit "match arms as branches" instruction: a documented,
deliberate divergence from the python precedent, not an oversight),
loops (`loop`/`while`/`for` expressions), calls (bare and
`obj.method(...)` dotted forms), field accesses (`field_expression`,
unrestricted to any receiver like `_python.py`'s `attribute` handling,
not `_typescript.py`'s `this.x`-only restriction, since rust has no
single universal receiver keyword), returns, and `use_declaration` ->
`NormalizedImport` (plain path, `as`-rename, one level of `{...}`
grouped list with one level of nested-group flattening, and `*`
wildcard).

PANIC/RESULT MAPPING DECISION (rust has no exceptions -- documented in
full in the module's own docstring, summarized here): `panic!`/
`unreachable!`/`todo!`/`unimplemented!` macro invocations ->
`NormalizedRaise` (exception_type e.g. `"panic!"`); `.unwrap()`/
`.expect(...)` method calls -> ALSO `NormalizedRaise` (rust's idiomatic
panic sites), in addition to their own `NormalizedCall`; a `return`/tail
`Err(...)` construction -> ALSO `NormalizedRaise(exception_type="Err")`,
in addition to its own `NormalizedReturn`; the `?` try-operator ->
`NormalizedRaise(exception_type="?")` (an implicit re-throw on Err
propagation); a `match` arm whose pattern's leading identifier is `Err`
-> `NormalizedCatch(exception_type="Err")` (the "match/Result handling
-> catches equivalent" mapping this ticket asked for) -- an `Ok(...)`
arm is not a catch, there being no python/JS "success" analogue in
`NormalizedCatch`. Every raise/catch mapping is IN ADDITION to (never
instead of) the construct's own literal event, since a check may want
either view.

Two real bugs were caught and fixed during hand-verification against
real `tree-sitter-rust` parses before writing the pytest suite (not
present in the final code): (1) a `use_wildcard` node (`use a::*;`)
carries no NAMED `path` field -- its path child is reached via its first
named child, not `child_by_field_name("path")`, which silently returned
`None`/empty module text; (2) a `field_expression` that is itself the
`function` field of its parent `call_expression` (`obj.method(...)`) was
being double-counted as a `NormalizedFieldAccess` in addition to its
correct `NormalizedCall` -- a method-call chain like
`self.name.clone().unwrap()` falsely registered `clone`/`unwrap` as
field reads. Fixed via `_rust_is_call_target`, which excludes exactly
that one node from `NormalizedFieldAccess` while still recursing into
its own `value` child (a genuine nested field read, e.g. `self.name`
inside the chain, is unaffected). A regression test
(`test_adapt_method_chain_does_not_confuse_calls_with_field_accesses`)
locks this in.

Verified against real `tree-sitter-rust` parses of hand-built `.rs`
fixtures (no shared `tests/fixtures` dir exists for rust either, matching
the TS precedent) -- 15 new tests (`TestRustAdapter`): one per entity kind
(imports incl. wildcard/grouped/renamed, struct named+tuple fields, enum
variants, function params/return-type with the "always False" default
note, trait methods + inherent impl attach, trait-impl base+overrides,
branches/loops/calls/field-accesses, the method-chain regression above,
match-arms-as-branches + loop kinds, panic!/unwrap/expect raises,
Err-return/`?`-operator raises + still-a-return, Result-match Err-arm
catch) plus one stays-sane realistic-snippet test combining every
construct at once (round-trips through pydantic (de)serialization, same
as the python/TS shape tests). `TestSharedCheckOnPythonAndRust` extends
T-0611's shared-check acceptance criterion to rust: the SAME
`_iter_normalized_functions`/`_normalized_is_complex` helpers (pure
`NormalizedModule` functions, no per-language branch) fire identically on
an equivalent long/deeply-nested python fixture (via `PythonAdapter`) and
rust fixture (via `RustAdapter`), unmodified.

`ruff check`/`ruff format` clean under `uv run ruff` (project-pinned);
`uv run ty check src/frob/arch/_rust.py` clean. REL001 fired (minor,
0.87.0 -> 0.88.0) for the new public `RustAdapter` API -- version bumped,
CHANGELOG.md entry added, `frob release stamp` run; scope extended for
`pyproject.toml`/`.frob-release.json`/`CHANGELOG.md`/`uv.lock` (the last
one's own version-pin line changed as a side effect of the pyproject.toml
bump, same SCOPE001 shape as T-0610's precedent). Deletion-filter (`git
diff main --diff-filter=D --stat`) empty.

Filed T-0743 (ex-draft, id lost at land) (mints a real T-#### id at land) for a
`NormalizedVariant` model extension to carry enum associated-data shape,
per the enum-variant limitation noted above.

### Changed
```
 tickets.md | 122 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 120 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestRustAdapter::test_is_a_language_adapter` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRustAdapter::test_adapt_imports` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRustAdapter::test_adapt_struct_named_and_tuple_fields` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRustAdapter::test_adapt_enum_variants_as_fields` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRustAdapter::test_adapt_function_params_and_return_type` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRustAdapter::test_adapt_trait_methods_and_impl_attach` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRustAdapter::test_adapt_trait_impl_notes_trait_as_base_and_sets_overrides` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRustAdapter::test_adapt_branches_loops_calls_field_accesses` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRustAdapter::test_adapt_method_chain_does_not_confuse_calls_with_field_accesses` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRustAdapter::test_adapt_match_arms_are_branches_and_loop_kinds` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRustAdapter::test_adapt_panic_macro_and_unwrap_expect_are_raises` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRustAdapter::test_adapt_err_return_and_try_operator_are_raises` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRustAdapter::test_adapt_result_match_err_arm_is_a_catch` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRustAdapter::test_adapt_stays_sane_on_realistic_snippet` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSharedCheckOnPythonAndRust::test_long_complex_function_flags_identically_across_languages` (pytest node id, verified passing when recorded)
