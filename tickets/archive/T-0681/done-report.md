## Done report

Extended `NormalizedModule` with a new `NormalizedTypeAlias` entity
(name/line/target_text) since a bare type-alias binding has no
fields/methods/members any existing entity could carry. Interface and
enum declarations map onto the existing `NormalizedClass` shape instead
(mirroring `_kotlin.py`'s interface precedent and `_rust.py`'s
`enum_item` precedent already in this repo): interface bases via
`extends_type_clause`, fields via `property_signature`, methods
(bodyless, `body_line_count=0`) via `method_signature`; enum members
(bare or with an explicit value) all become `NormalizedField` entries
with no type/bases/methods.

`TypeScriptAdapter._ts_build_module` now dispatches
`interface_declaration`/`enum_declaration`/`type_alias_declaration`
(including through an `export` wrapper, matching the existing
class/function unwrap). TSX support needed no adapter change at all:
`.tsx` already carries the `"typescript"` `NormalizedModule.language`
label per `frob.lang`'s extension table (only the tree-sitter grammar
differs, `tsx` vs `typescript`), and a component function/arrow-function
returning JSX already maps onto `NormalizedFunction` through the
existing `function_declaration`/`lexical_declaration`-arrow paths; JSX
nodes inside a body simply recurse through the existing generic event
walk with no special-casing needed.

Fixed one pre-existing test (`test_adapt_class_bases_and_fields`) that
asserted an interface fixture was NOT in `module.classes` -- now that
interfaces map onto `NormalizedClass`, `Greeter` correctly appears there
alongside `Base`/`Animal`.

Added six new tests: interface (bases/fields/bodyless methods), enum
(members regardless of assigned value), type alias (two aliases,
target_text), export-wrapped variants of all three, and a TSX component
fixture (interface + two component shapes with JSX bodies) with a
pydantic round-trip check.

### Changed
```
 src/frob/arch/_normalized.py |  33 +++++
 src/frob/arch/_typescript.py | 156 +++++++++++++++++++++-
 tests/unit/test_arch.py      | 143 +++++++++++++++++++-
 3 files changed, 311 insertions(+), 21 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_interface_declaration` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_enum_declaration` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_type_alias_declaration` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_exported_interface_enum_type_alias` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_tsx_component` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_class_bases_and_fields` (pytest node id, verified passing when recorded)

### Captured claims
- tests: full `tests/unit/test_arch.py` suite (100 tests) passed; `uv run frob test --base main` also passed on the touched set
- gates: `uv run frob check --ticket T-0681` -- 0 errors (all gates pass: ARCH, COV, DEAD, DEPR, DOC, DRIFT, INV, LANG, PERF, PII, PLACE, REF, REG, REL, SEC, TEST, TICK, WAIVE, WALK)
