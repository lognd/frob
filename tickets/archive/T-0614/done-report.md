## Done report

Adds `KotlinAdapter` (`frob.arch._kotlin`), the fourth `LanguageAdapter`
(T-0609) implementation after T-0610's `PythonAdapter`/T-0611's
`TypeScriptAdapter`/T-0612's `RustAdapter`, mapping a `tree-sitter-kotlin`
parse (via `tree-sitter-language-pack`, the grammar T-0613 already wired
standalone through `frob.lang._walk_kotlin.parse_kotlin`/`raw_kotlin_tree`)
onto the T-0609 `NormalizedModule` shape. Kept in its own module
`src/frob/arch/_kotlin.py` (never `_normalized.py`, which stays a pure
tree_sitter-free model module per T-0609's design, and never
`frob.lang._walk_kotlin.py`, which is the raw tree-sitter escape hatch, not
this architectural model) -- exactly mirroring `_rust.py`'s placement
relative to `_normalized.py`, the T-0611 review correction every sibling
adapter since has followed; scope extended (`frob ticket scope --add
src/frob/arch/_kotlin.py`) for it.

GRAMMAR QUIRK THAT SHAPED THIS MODULE: verified interactively before
writing any adapter code that `tree-sitter-kotlin` (as bundled by
`tree-sitter-language-pack`) exposes almost NO named fields --
`node.child_by_field_name(...)` (the `_child`/`frob.lang.child_by_field`
helper every sibling adapter leans on) returns `None` for essentially every
node type here. Every lookup in `_kotlin.py` is therefore
positional/type-based (`_kt_child_of_type`: scan `node.children` for a
specific `node.type`), a structural difference from `_typescript.py`/
`_rust.py`, not a stylistic one. One real bug this surfaced during
hand-verification (fixed before writing the pytest suite): a default
parameter value's `=`/value tokens are NOT children of the `parameter`
node itself in kotlin's grammar (unlike TS's `optional_parameter`) -- they
are siblings of `parameter` one level up, inside `function_value_
parameters`. `_kt_normalize_params` originally checked `parameter`'s own
children for `has_default` and always returned `False`; fixed to check the
immediately-following sibling in `function_value_parameters`'s own
children instead.

`KotlinAdapter` maps: `class_declaration` (kotlin's grammar uses this SAME
node type for both `class` and `interface`, so both come back as
`NormalizedClass` for free), `delegation_specifier` supertypes/interfaces
(whether wrapping a `constructor_invocation` supertype call or a bare
`user_type` interface reference) -> `bases`; `primary_constructor`
`class_parameter`s that carry a `val`/`var` `binding_pattern_kind` (a plain
constructor parameter with neither is NOT a property and is NOT mapped --
kotlin's own property-vs-parameter distinction) plus `class_body`
`property_declaration`s -> `fields`; `class_body` `function_declaration`s
-> `methods`; `member_modifier` `override` -> `NormalizedFunction.
overrides`; top-level `function_declaration`s; branches (`if_expression`,
`conjunction_expression`(`&&`)/`disjunction_expression`(`||`) as their own
distinct boolean node types -- kotlin's grammar, unlike TS/rust, does not
fold these into one `binary_expression` with an `operator` field -- and,
per this ticket's explicit "when as branches, each when-entry as a branch
arm" instruction, EVERY `when_entry` counts as its own branch, mirroring
`_rust.py`'s documented `match_arm`-per-branch divergence from
`_python.py`'s deliberate match/case exclusion); loops (`for_statement`,
`while_statement`, `do_while_statement`); calls (`call_expression`, bare
and `obj.method(...)`/`this.method(...)` dotted forms); `this.x` field
accesses (`navigation_expression` reads, `directly_assignable_expression`
write targets -- kotlin's grammar uses two DIFFERENT node types for the
read vs. write shape of the same `this.x` syntax); returns and throws
(`jump_expression` with a leading `return`/`throw` keyword child);
`catch_block` -> `NormalizedCatch`; and `import_header` -> `NormalizedImport`
(plain/`as`-aliased/`*`-wildcard forms -- kotlin has no `{...}` grouped-
import syntax, unlike rust's `use a::{b, c};`).

A method-chain false-positive fix ported directly from T-0612's own
review-caught bug: `this.compute()` -- the `navigation_expression`
`this.compute` is the CALLEE of its own `call_expression`, and without
`_kt_is_call_target`'s exclusion (mirroring `_rust_is_call_target`
exactly) it would falsely register `compute` as a field READ in addition
to the correct `NormalizedCall`. Caught and fixed via a real hand-parsed
check before writing the pytest suite, with a regression test
(`test_adapt_method_chain_does_not_confuse_calls_with_field_accesses`)
locking it in.

NOT mapped (no `NormalizedModule` entity exists for these, or the
construct is out of this ticket's own "open/data/sealed" class scope --
documented in the module's own docstring, not silently dropped): `enum
class`'s `enum_class_body`/`enum_entry` (a DIFFERENT node type from a
regular class's `class_body`, so an enum class comes back with empty
fields/methods -- the same "no NormalizedVariant entity" limitation
`_rust.py`'s `enum_item` note documents); `object_declaration` (kotlin's
singleton syntax, a distinct node type `_kt_build_module`'s top-level walk
never visits); a `secondary_constructor` (a class's own non-primary
`constructor(...) { ... }` body, a real function body kotlin's grammar
gives its own node type, not mapped to `NormalizedFunction`).

DISPATCH-WIRING INVESTIGATION (T-0613's own docstring says "central
dispatch wiring... likewise left to T-0614"): investigated wiring `.kt`/
`.kts` into `frob.lang.__init__`'s `_EXTENSION_TABLE` so
`TestKotlinAdapter` could build real Kotlin trees via `frob.lang.raw_tree`
exactly like `TestRustAdapter`/`TestTypeScriptAdapter` do (scope was
briefly extended for `src/frob/lang/__init__.py` to do this). Reverted
after confirming it would be unsafe on its own: `_EXTENSION_TABLE` also
drives `parse_file`'s general `extract()` call, which dispatches through
`_extract.py`'s `_WALKERS`/`COMMENT_TYPES` tables -- neither has a kotlin
entry (T-0613 added only `parse_kotlin`/`raw_kotlin_tree`, no `RawSymbol`
walker), so any real `.kt` file reaching `parse_file`/`frob check`'s repo
scan after this wiring would `KeyError`, not gracefully report
`UnsupportedLanguage`. Filed T-0723 (ex-draft, id lost at land) (mints a real T-#### id at
land) for the actual central-dispatch wiring (a `_walk_kotlin` `RawSymbol`
walker plus `_EXTENSION_TABLE`/`COMMENT_TYPES`/`_WALKERS` registration
together) as a follow-up, not folded into this ticket. `TestKotlinAdapter`/
`TestSharedCheckOnPythonAndKotlin` instead call `frob.lang._walk_kotlin.
parse_kotlin` directly (source bytes -> `Tree`, already public and
standalone per T-0613) -- no dispatch-table change needed for this
ticket's own acceptance criterion.

Verified against real `tree-sitter-kotlin` (via `tree-sitter-language-
pack`) parses of hand-built kotlin snippets (no shared `tests/fixtures`
dir exists for kotlin either, matching the TS/rust precedent) -- 12 new
`TestKotlinAdapter` tests: one per entity kind (imports, interface+class
bases/fields/methods including the bodyless interface method, data-class
constructor properties, sealed-class-with-no-body, override modifier,
function params/return-type including the has_default fix above,
branches/loops/calls/field-accesses, the method-chain regression above,
when-entries-as-branches + for/while/do-while loop kinds, throw/catch)
plus one stays-sane realistic-snippet test combining every construct at
once (round-trips through pydantic (de)serialization, same as the
python/TS/rust shape tests). `TestSharedCheckOnPythonAndKotlin` extends
T-0611/T-0612's shared-check acceptance criterion to kotlin: the SAME
`_iter_normalized_functions`/`_normalized_is_complex` helpers (pure
`NormalizedModule` functions, no per-language branch) fire identically on
an equivalent long/deeply-nested python fixture (via `PythonAdapter`) and
kotlin fixture (via `KotlinAdapter`), unmodified -- this ticket's own
acceptance criterion, proven directly.

Gates: `frob check --ticket T-0614` -- 0 findings mention T-0614 itself.
2 `gate:COV` COV003 errors remain in the full run, both against ticket
T-0705's evidence in `tests/system/test_cli_check.py` (stale evidence ids
for tests that no longer resolve there) -- unrelated to `frob.arch`/this
ticket's scope, the same drift-from-main-moving-target shape T-0610's own
Done report documents for a different ticket's stale evidence.

`ruff check`/`ruff format` clean under both the PATH `ruff` and the
project-pinned `uv run ruff`; `uv run ty check src/frob/arch/_kotlin.py`
clean. REL001 fired (minor, 0.88.0 -> 0.89.0) for the new public
`KotlinAdapter` API -- version bumped, `CHANGELOG.md` entry added, `frob
release stamp` run; scope extended for `pyproject.toml`/
`.frob-release.json`/`uv.lock`/`CHANGELOG.md` (the T-0610/T-0611/T-0612
precedent for this exact SCOPE001 shape). PRE001 fired against the sweep
recorded before the final scope additions; refreshed via `frob ticket
sweep T-0614` after scope settled. Deletion-filter (`git diff main
--diff-filter=D --stat`) empty.

Filed T-0723 (ex-draft, id lost at land) (mints a real T-#### id at land) for the actual
kotlin central-dispatch wiring (`_walk_kotlin` `RawSymbol` walker +
`_EXTENSION_TABLE`/`_extract.py` registration), per the investigation
above.

### Changed
```
 tickets.md | 686 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 669 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestKotlinAdapter::test_is_a_language_adapter` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_imports` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_class_bases_fields_and_methods` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_data_class_constructor_properties` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_sealed_class_with_no_body` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_override_modifier` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_function_params_and_return_type` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_branches_loops_calls_field_accesses` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_method_chain_does_not_confuse_calls_with_field_accesses` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_when_entries_are_branches_and_loop_kinds` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_throw_and_catch` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_stays_sane_on_realistic_snippet` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSharedCheckOnPythonAndKotlin::test_long_complex_function_flags_identically_across_languages` (pytest node id, verified passing when recorded)
