## Done report

Wires T-1824's per-symbol deflation heuristic into a real gate Violation
(TEST019), closing the gap T-1824 could not reach from its own declared
scope.

- `CoverageData.suspect_deflated_symbols: tuple[str, ...] = ()`
  (frob.gates._models) carries `_suspect_deflated_symbols`'s computed
  symref list out of `load_coverage` (frob.gates._coverage), replacing the
  T-1824 log-only path.
- `_test019_deflated_symbols(data: CoverageData) -> tuple[Violation, ...]`
  (frob.gates) emits a WARN-severity TEST019 Violation per non-empty
  suspect list, folded into `_test005`'s dispatch alongside
  TEST008/TEST011/TEST017/TEST012.
- TEST019 registered in `_KNOWN_GATE_RULES` (frob.gates._waive).
- docs/modules/gates.md: TEST019 row added to the rule table, the
  `frob:enumerates` anchor list updated, and a new "TEST019
  (T-1824/T-1877)" section added describing the heuristic, its
  corroboration requirement, and the T-1824/T-1877 scope split.
- New test file tests/test_gates_test019.py (a dedicated file, not
  tests/test_gates.py, because T-1887 held a live cross-worktree lease on
  that file when this ticket was worked -- T-1868): one test proves
  TEST019 fires on a suspect symref, one proves it does NOT fire on clean
  (empty) input.
- `docs/design/registry/check-coverage.yaml` now carries the real
  `CHK-GATE-TEST019` entry (`handled_by:TEST019`, same shape as the
  existing TEST017/TEST018 entries), `gate_rule_total` bumped 292 -> 293.
  T-1888's cross-worktree lease on this file cleared before this land, so
  the REG009 waiver on `_test019_deflated_symbols`'s `frob:enforces
  CHK-GATE-TEST019` directive was removed -- the rule is now genuinely
  catalogued, not waived-and-deferred.
- Draft T-1898 (the follow-up that would have added this same
  registry entry) is now redundant and was dropped with a reason pointing
  at this land.

### Evidence
- `tests/test_gates_test019.py::TestTest019DeflatedSymbols::test_flags_suspect_symbol` (pytest node id, verified passing when recorded)
- `tests/test_gates_test019.py::TestTest019DeflatedSymbols::test_clean_when_no_suspects` (pytest node id, verified passing when recorded)

### Changed
```
 docs/modules/gates.md              | 43 +++++++++++++++++++++++++++++++++-
 src/frob/gates/__init__.py         | 44 ++++++++++++++++++++++++++++++++++
 src/frob/gates/_coverage.py        |  8 +++----
 src/frob/gates/_models.py          |  8 +++++++
 src/frob/gates/_waive.py           |  6 +++++
 tests/test_gates_test019.py        | 42 +++++++++++++++++++++++++++++++++
 tickets/T-1877/done-report.md      | 47 +++++++++++++++++++++++++++++++++++++
 tickets/T-1877/ticket.md           | 48 +++++++++++++++++++++++++++++++++++++-
 tickets/T-1898/ticket.md | 26 +++++++++++++++++++++
 9 files changed, 266 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_gates_test019.py::TestTest019DeflatedSymbols::test_flags_suspect_symbol` (pytest node id, verified passing when recorded)
- `tests/test_gates_test019.py::TestTest019DeflatedSymbols::test_clean_when_no_suspects` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 3 error(s), 1308 warning(s), 694 waived
- error-findings: invalid-argument-type@src/frob/app/ticket_runner/_lifecycle.py, invalid-argument-type@tests/test_tickets_scope_mutation.py, invalid-argument-type@tests/unit/gates/test_sys_interface_canonical_order.py
