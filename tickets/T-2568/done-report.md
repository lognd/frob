## Done report

Extended NormalizedCallArg with a raw text field (ident's superset -- entry.name is an attribute access, not a bare identifier, so ident alone could never represent it) and added _isdigit_guard_discharges to the may-raise resolver: a preceding .isdigit() guard on int(x)/float(x)'s own argument expression now discharges the ValueError the unguarded call would otherwise contribute, matching this file's own line-adjacency-proxy textual-match convention. Fixed every isdigit-guarded EXHAUST002 finding in the corpus (12 of 15 measured at fix time, up from 8 at ticket filing since the corpus grew under fleet activity). Two remaining model-limit classes (a regex-group match.group(N) guard needing real local flow, and a list-comprehension whose if-clause guard executes before its own output expression in source order) are waived per-site with follow-up tickets T-3473/T-3474 rather than forced with an unsound generalization; two unrelated new EXHAUST002 findings (StopIteration, TicketLockUnavailable) are tracked separately in T-3475, out of this ticket's guard-predicate scope.

### Changed
```
 docs/modules/arch.md           |  37 +++++++++-
 scripts/_require_python.py     |   6 ++
 scripts/wait_for_land_slot.py  |   6 ++
 src/frob/arch/_mayraise.py     |  64 ++++++++++++++++-
 src/frob/arch/_normalized.py   |  17 ++++-
 src/frob/arch/_python.py       |   2 +
 src/frob/process/_proc_scan.py |   7 ++
 tests/unit/test_arch.py        | 151 +++++++++++++++++++++++++++++++++++++++++
 tickets/T-2568/done-report.md  |  19 ++++++
 tickets/T-2568/ticket.md       |   7 +-
 10 files changed, 312 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestIsdigitGuardDischarge::test_guarded_int_call_discharges_value_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestIsdigitGuardDischarge::test_unguarded_int_call_still_raises_value_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestIsdigitGuardDischarge::test_isdigit_guard_on_a_different_expression_does_not_discharge` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestIsdigitGuardDischarge::test_guard_several_unrelated_branches_before_the_call_still_discharges` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 16 error(s), 4453 warning(s), 866 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-2568, REL001@src/frob/__init__.py, SELFAUDIT001@src/frob/gates/_land_parity.py, SELFAUDIT001@src/frob/gates/_policy_weakening_gate.py, SELFAUDIT001@tests/unit/strata/test_strata_core_gil.py, SELFAUDIT001@tests/unit/test_land_parity_gate.py, SELFAUDIT001@tests/unit/test_sync_claude_config_stale_guard_t3408.py, SELFAUDIT001@tests/unit/verify/test_worker.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
