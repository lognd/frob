## Done report

EPIC T-0330's DIP slice of the ARCH1xx catalog. Adds a new module
`src/frob/arch/_layering.py` (a separate module from `_solid.py` since
the layering contract needs a PROJECT-WIDE import graph, not one file's
`NormalizedModule`): `check_layering_violations` and
`check_no_di_construction`.

`check_layering_violations`: a `frob.toml`-declared `[arch.layering]`
allowed-module-dependency graph, import-linter style (named layers +
an explicit allowed-edge set -- every cross-layer edge must be named
explicitly, not "higher may import any lower" by default). Walks every
python file under a declared layer, resolves imports via
`frob.lang.extract_imports`/`resolve_local_import` (the SAME pair
`frob.app.cycle_runner._build_graph` already uses for cycle detection --
reused, not re-derived), and flags a resolved edge into a declared layer
not present in the source layer's `allow` list. Addresses the epic's
adversarial-hardening note on two fronts: (1) re-export resolution --
`_resolve_reexports` follows one bounded hop through an `__init__.py`
target's own local imports so a package-boundary import doesn't hide the
real submodule coupling; (2) fail-closed on dynamic indirection --
`_has_dynamic_import` flags a layered file containing
`importlib.import_module(`/`__import__(` as its own violation, since this
scan cannot prove such a file's real import set from static imports
alone.

`check_no_di_construction`: written once against `NormalizedModule`
(T-0609), same convention as `_solid.py`'s checks. Flags a method/function
(excluding `__init__`/`__new__`, and factory-named functions) whose OWN
body constructs a same-file concrete class inline via a bare
`ClassName(...)` call -- the collaborator should have been received via
injection instead.

Added a REAL, minimal `[arch.layering]` worked example to this repo's own
`frob.toml` (inert -- not wired into `frob check`, matching every sibling
ARCH1xx ticket's disclosed gate-wiring cut): `src/frob/lang` (leaf parsing
utility) may never import back from `src/frob/app` (CLI/orchestration
layer), which may depend on `lang`.

SCOPE NOTE: extended T-0620's declared scope via `frob ticket scope
--add` to include `src/frob/arch/_models.py` (two new `ArchCategory`
values, `dip-layering-violation`/`no-di-construction`) -- the ticket's
original scope omitted it while every sibling ticket in this cluster
(T-0617/T-0618/T-0619) already listed it for the identical mechanical
reason. Reasoned via `--reason-file`, not routed around.

### Changed
```
docs/modules/arch.md          | DIP layering contract + no-DI construction sections, 2 top-table rows
frob.toml                     | +1 real [arch.layering] worked example (inert)
src/frob/arch/_layering.py    | new file, ~330 lines
src/frob/arch/_models.py      | 2 new ArchCategory values
tests/unit/test_arch.py       | 10 new tests across 4 new test classes
```

### Evidence
Collected via `pytest tests/unit/test_arch.py -p no:cacheprovider -q`
(104 passed, full file) and `--collect-only` (all 10 node ids below
resolved):
- tests/unit/test_arch.py::TestLayeringConfig::test_layer_for_longest_prefix_match
- tests/unit/test_arch.py::TestLayeringConfig::test_layer_for_unmatched_path_is_none
- tests/unit/test_arch.py::TestLoadLayeringConfig::test_missing_frob_toml_returns_none
- tests/unit/test_arch.py::TestLoadLayeringConfig::test_parses_declared_layers_and_allow_table
- tests/unit/test_arch.py::TestLayeringViolations::test_disallowed_cross_layer_edge_flagged
- tests/unit/test_arch.py::TestLayeringViolations::test_allowed_cross_layer_edge_not_flagged
- tests/unit/test_arch.py::TestLayeringViolations::test_dynamic_import_in_layered_file_flagged
- tests/unit/test_arch.py::TestNoDiConstructionSmell::test_inline_construction_outside_init_flagged
- tests/unit/test_arch.py::TestNoDiConstructionSmell::test_construction_inside_init_not_flagged
- tests/unit/test_arch.py::TestNoDiConstructionSmell::test_construction_inside_factory_function_not_flagged

`frob check --only <lint|static|gates-fast|gates-native|gates-security>
--ticket T-0620` (chunked loop), measured after a `git merge main` (main
advanced mid-session) and a `.frob/pytest-collect.json` cache rebuild.

### Filed
none new -- the one scope gap found (missing `_models.py` in T-0620's own
declared scope) was closed via `frob ticket scope --add` with a reason,
not filed as a separate ticket, since it is this same ticket's own
implementation blocked on it.

### Gates
`frob check --only <lint|static|gates-fast|gates-native|gates-security>
--ticket T-0620`: lint/static/gates-native/gates-security all 0 errors.
gates-fast has exactly ONE remaining error, `TICK003` (64 closed tickets
sitting un-archived in tickets.md, threshold 60) -- pre-existing repo-wide
housekeeping debt, not caused by or scoped to this ticket's files;
disclosed here rather than silently left out. An earlier gates-fast pass
also showed 43 `COV003` findings (stale test-collection-cache entries for
unrelated tickets T-0660/T-0661/T-0680/T-0719, whose evidence pointed at
`tests/test_vet.py` classes this worktree's PRE-merge snapshot did not
yet have) -- these cleared entirely after `git merge main` pulled in the
532-line `tests/test_vet.py` update those tickets' own lands had already
made; not a regression from this ticket.

### Changed
```
 docs/modules/arch.md       | 176 +++++++++++++++++
 frob.toml                  |  24 +++
 src/frob/arch/_layering.py | 380 ++++++++++++++++++++++++++++++++++++
 src/frob/arch/_models.py   |  18 ++
 src/frob/arch/_solid.py    | 278 +++++++++++++++++++++++++-
 tests/unit/test_arch.py    | 472 +++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                 | 119 +++++++++++-
 7 files changed, 1461 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestLayeringConfig::test_layer_for_longest_prefix_match` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestLayeringConfig::test_layer_for_unmatched_path_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestLoadLayeringConfig::test_missing_frob_toml_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestLoadLayeringConfig::test_parses_declared_layers_and_allow_table` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestLayeringViolations::test_disallowed_cross_layer_edge_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestLayeringViolations::test_allowed_cross_layer_edge_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestLayeringViolations::test_dynamic_import_in_layered_file_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestNoDiConstructionSmell::test_inline_construction_outside_init_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestNoDiConstructionSmell::test_construction_inside_init_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestNoDiConstructionSmell::test_construction_inside_factory_function_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
