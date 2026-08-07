## Done report

Classified all raw DEAD001 findings on this repo's own tree (62 raw
diagnostics before the fix: 18 real WARN + 44 already/wrongly-waived
NOTE) before changing anything.

Root cause found: `dead_symbol_gate` never set `Violation.symref`, so
`_match_waiver`'s symbol-exact path was dead code for this rule -- every
DEAD001 waiver fell back to file-scope matching, silently forgiving
EVERY DEAD001 in the same file, not just its own target. Fixed by
passing `symref=symref` into the `Violation` constructor.

After the symref fix, re-measured: 20 real warnings remained (2 more
surfaced than the original 18, because 2 were previously over-suppressed
by the same file-scope bug -- TicketSpec._validate_blocked_by_field/
_validate_parent_field).

Per-finding classification of the 20:
- 9 pydantic `@field_validator` methods (AppConfig x6, TicketSpec x2,
  AcceptanceCriterion x1): rule-gap, not real debt -- added
  `_is_pydantic_validator` rescue (mirrors WIRE001's autouse-fixture
  rescue shape). Also removed the one pre-existing `frob:waive DEAD001`
  on AcceptanceCriterion._normalize_evidence as redundant now that the
  rescue covers it structurally (declared below).
- 5 `@pytest.fixture(autouse=True)` fixtures (tests/conftest.py x2,
  tests/test_ticket_land.py x2, tests/unit/test_ticket_store.py x1):
  rule-gap -- DEAD001 lacked the autouse-fixture rescue WIRE001 already
  has. Moved `_is_autouse_pytest_fixture`/`_AUTOUSE_FIXTURE_RE` from
  `frob.gates._wire` into `_dead_symbols.py` (NO DUPLICATION: `_wire.py`
  now imports it back) and wired it into DEAD001 too.
- 5 genuine cross-package callers (real debt in the gate's own
  documented package-scoped-callgraph blind spot, not the symbol):
  `_add_explore_parser` (called from `__main__.py`),
  `_write_post_land_verify_marker`/`_clear_post_land_verify_marker`
  (called from `_land_cmd.py`), `_scan_line` (called from
  `gates/_secrets.py` and `app/telemetry.py`) -- waived with the exact
  reason pattern this repo's own `_cli_parsers/_core.py` etc. already
  use for the identical shape (T-1024 precedent), verified each real
  caller by grep before waiving.
- 1 genuinely dead: `_run_post_land_sweep_or_exit` in
  `app/ticket_runner/_land_cmd.py` -- its logic was inlined directly
  into the land CLI entrypoint with an added T-1523 marker-write/clear
  wrapper, leaving the standalone wrapper an orphaned duplicate with
  zero real callers (only prose mentions). DELETED, and fixed the 3
  stale docstring/comment pointers to it (2 in the same file, 1 in
  tickets/_models.py) so no dangling reference survives.
- 1 genuinely dead: `_reset_span_cache` in vet/_capability_core.py --
  its own docstring already admitted "nothing outside this module's own
  tests needs to call it", and no test does either. DELETED (repo
  directive: prefer deletion over waiver for vestigial code).

Verification: `frob check --only dead_symbols --json`
(FROB_NO_GATE_CACHE=1) shows 0 warning-severity DEAD001 findings after
this ticket, down from 18 before. `frob check --land-parity`: clean, 0
unscoped errors. `uv run ruff check` and PATH `ruff check` both clean on
every touched file. Full tests/test_gates.py (664 tests),
tests/unit/test_ticket_store.py + tests/test_ticket_land.py (317 tests)
all pass.

Waive-directive deletions (declared per land-deletion-filter discipline):
src/frob/tickets/_models.py: DEAD001 (AcceptanceCriterion._normalize_evidence waiver removed, superseded by _is_pydantic_validator rescue)

### Changed
```
 tickets.md | 210 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 210 insertions(+)
```

### Evidence
- `tests/test_gates.py::TestDeadSymbolGate::test_unwired_private_function_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_called_private_helper_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_waiver_directly_above_symbol_suppresses_it` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_pydantic_field_validator_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_autouse_pytest_fixture_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_dunder_method_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_test_function_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_tests_edge_target_is_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 0 error(s), 1134 warning(s), 844 waived
- error-findings: none (measured, zero errors)
