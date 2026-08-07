## Done report

Decision (consistent with T-0168): design-file `flow`/`boundary`/`operation`/
`scenario` declarations are exempt from TEST003's package-level
integration-test count (they own no pytest surface, same reasoning as the
existing TEST001/TEST002 exemption), AND design ids get a real,
enforced e2e-binding obligation instead of just a bare exemption -- a new
rule TEST009 requiring `min_design_e2e` (default 1) `frob:tests
kind="e2e"` edges per `.strata` design file, WARN severity (same as
TEST003, which it replaces for this directory).

Changed:
- `src/frob/gates/__init__.py::_public_packages` -- excludes
  `record.id.path.endswith(".strata")` from TEST003's package derivation.
- `src/frob/gates/__init__.py::_design_files` -- new, lists `.strata`
  files with at least one public construct.
- `src/frob/gates/__init__.py::_edges_for_design_file` -- new, e2e edges
  targeting a design file or a symbol declared in it.
- `src/frob/gates/__init__.py::_test009` -- new, the TEST009 gate check.
- `src/frob/gates/__init__.py::test_gate` -- wires `_test009` into the
  aggregate; docstring updated (TEST001..TEST009).
- `src/frob/gates/__init__.py::_KNOWN_GATE_RULES` -- added `"TEST009"`.
- `src/frob/gates/_models.py::TestPolicy.min_design_e2e` -- new field,
  default 1.
- `tests/test_gates.py` -- three new tests (below).

`src/frob/lang/_walk_strata.py` was in scope but needed no change --
`.strata` construct extraction already gives every design id a `symref`
(`path::qualname`) TEST009 can bind a `frob:tests` edge to; the gap was
purely in gate logic, not extraction.

Evidence:
- `tests/test_gates.py::TestTestGate::test_test003_exempts_strata_design_files`
  -- TEST003 no longer fires with `v.file == "design"` for a design/*.strata
  fixture.
- `tests/test_gates.py::TestConventionUnitBinding::test_test009_fires_on_unbound_design_file`
  -- TEST009 fires on a `.strata` design file with no e2e edge.
- `tests/test_gates.py::TestConventionUnitBinding::test_test009_satisfied_by_e2e_edge`
  -- a collected `frob:tests ... kind="e2e"` edge satisfies TEST009.

Full `tests/test_gates.py` run: 145 passed (`uv run pytest tests/test_gates.py -q`).
`uv run frob test --base main`: touched-set selection (`tests/test_gates.py`
plus 2 rippled node ids) -> `[PASS] python exit=0`.
`uv run ruff check src/frob/gates/__init__.py src/frob/gates/_models.py
tests/test_gates.py`: all checks passed.

Gates: `uv run frob check --ticket T-0225` clean -- `gates 0 errors, 44
warnings, 25 waived`, overall `frob check . [WARN] 0 errors 174 warnings`
(exit 0). The repo's own `design/frob.strata` (and the litmus `.strata`
fixtures under `design/litmus/`) now surface as new TEST009 WARN findings
since none carry an e2e binding yet -- WARN severity, consistent with
TEST003's own severity, so this does not fail `frob check`; binding them
is follow-up work, not part of this ticket's declared scope.

Filed: none.
