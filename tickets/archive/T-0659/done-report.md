## Done report

## Done report

Changed:
src/frob/vet/_capability.py::_py_target_is_dangerous
src/frob/vet/_capability.py::_bind_py_name
src/frob/vet/_capability.py::_bind_import_statement
src/frob/vet/_capability.py::_bind_import_from_statement
src/frob/vet/_capability.py::_resolve_py_expr
src/frob/vet/_capability.py::_resolve_py_identifier
src/frob/vet/_capability.py::_resolve_py_attribute
src/frob/vet/_capability.py::_attr_rebind_lookup
src/frob/vet/_capability.py::_build_py_alias_table
src/frob/vet/_capability.py::_record_py_default_param_aliases
src/frob/vet/_capability.py::_record_py_alias
src/frob/vet/_capability.py::_record_py_destructure_alias
tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution (new, 14 tests)

Scope of the fix (docs/design/capability-evasion-taxonomy.md's Python
table, 13 static-resolvable rows): closes the remaining gaps beyond
T-0328/T-0337, matching the ticket's explicit list:

- Chained assignment (`a = b = subprocess.run; a(x)`): `_resolve_py_expr`
  now peels through a nested `assignment` node RHS instead of giving up.
- Tuple/list unpacking bind and starred unpacking bind
  (`f, g = subprocess.run, os.system`; `f, *rest = [subprocess.run]`):
  new `_record_py_destructure_alias`, positional correspondence with
  correct splat-before/splat-after semantics.
- Default-arg forwarding a callable (`def h(cb=subprocess.run): cb(x)`):
  new `_record_py_default_param_aliases`, keyed to the function's own
  scope id (parameters already shadow unconditionally).
- Attribute rebinding (`mod.run = subprocess.run; mod.run(x)`): new
  `_attr_rebind_lookup` / `_record_py_alias`'s attribute branch --
  best-effort, BY-NAME object identity only (no real points-to; disclosed
  in the docstring, not a claimed general points-to solution).
- Star-import re-export chain (`from subprocess import *; run(x)`):
  `_bind_import_from_statement`'s wildcard branch + `_PY_WILDCARD_TABLE_KEY`
  sentinel fallback in `_resolve_py_identifier` -- ONLY for modules
  `DANGEROUS_OPERATIONS` already curates (`_PY_WILDCARD_DANGEROUS_MODULES`);
  a wildcard import of an untracked module still resolves nothing (honest
  under-approximation, tested:
  test_star_import_untracked_module_not_claimed).
- Conditional/try-except import-fallback aliasing: `_bind_py_name` keeps a
  dangerous binding from being silently overwritten by a later benign one
  in the SAME import table (order-independent -- tested with the dangerous
  branch first AND second).
- Closure capture and `with`/`except ... as` binding rows were already
  covered by the pre-existing T-0328/T-0337 machinery; verified by
  inspection, no code change needed for those two rows.

Honest disclosed cuts (not silently narrowed):
- Attribute rebinding is object-IDENTITY-BY-NAME only, not real points-to
  (two different `mod` objects with the same local name in different
  scopes are not distinguished beyond normal scope nesting). Matches the
  taxonomy's own "(needs points-to on mod)" annotation -- documented as a
  best-effort resolution, not a full points-to solver.
- Star-import re-export only fires for modules already in
  `DANGEROUS_OPERATIONS` (subprocess, os, builtins, ...). A wildcard
  import of an arbitrary untracked third-party module still resolves to
  nothing, per the taxonomy's own "degrades to opaque" caveat for this
  row -- not attempted, and honestly not claimed.
- Nested destructuring patterns (`(a, b), c = ...`) are not recursed into;
  only a single flat `pattern_list` level is handled.
- The `as` in `with`/`except` binding row and closure-capture row are
  covered by pre-existing T-0328/T-0337 mechanics; no new litmus fixture
  was added for them in this pass since they already had coverage before
  T-0659 and the row itself (per the taxonomy doc) is "not itself
  dangerous, just part of the binding family".

Evidence: node ids observed collected via
`uv run pytest tests/test_vet.py -k TestCapabilityScanTaxonomyClosureResolution --collect-only -q -o addopts=""`
(14/227 collected) and all 14 pass individually and as part of the full
`tests/test_vet.py` suite (227 passed in 27.52s, `uv run pytest
tests/test_vet.py -p no:cacheprovider`). All 14 bound via `frob ticket
evidence T-0659 <node> --accepts <N>`: 9 detection-case tests bound to
acceptance[0] ("every aliased dangerous call is detected"), 5
no-regression tests (benign destructuring, untracked-module wildcard, both
branches safe) bound to acceptance[1] ("benign/shadowing binding stays
silent").

Filed: none -- every construct in the ticket's plan was implementable
in-scope; no out-of-scope discovery required a new ticket.

Gates: `FROB_AGENT=1 FROB_WORKTREE=<worktree> uv run frob check --ticket
T-0659 --only <stage>` clean for all five stage groups (lint, static,
gates-fast, gates-security, gates-native) after re-running `frob ticket
sweep T-0659` once mid-session (the pre-work sweep goes stale against new
edits -- PRE001 caught it, re-swept, then gates-fast passed 0 errors).
No new errors in any stage; only pre-existing waived warnings (unrelated
to this change) remain. `uv run ruff format` / `ruff check --fix` applied
once to reach 0 lint errors.

### Changed
(no changed files detected)

### Evidence
- `tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_chained_assignment_outer_target_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_chained_assignment_inner_target_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_tuple_unpack_destructuring_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_tuple_unpack_second_element_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_starred_unpack_leading_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_starred_unpack_trailing_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_default_arg_forwarding_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_attribute_target_rebind_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_star_import_reexport_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_conditional_import_fallback_dangerous_first_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_conditional_import_fallback_dangerous_second_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_benign_destructuring_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_star_import_untracked_module_not_claimed` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_conditional_import_fallback_both_safe_not_detected` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 14 passed (from 14 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
