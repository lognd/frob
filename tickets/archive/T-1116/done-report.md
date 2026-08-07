## Done report

Changed:
tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness.test_every_deferred_entry_targets_an_open_ticket

The test's own precondition assertion (`assert deferred, "expected at
least one deferred entry to check against"`) was stale: confirmed via
direct grep of docs/design/registry/weaknesses.yaml that zero entries
carry a DEFERRED disposition on current main -- every previously
deferred entry has since been resolved to checkable/duplicate-of/
out-of-scope. This is the goal state, not a regression, matching the
identical precedent already landed for the sibling
test_registry_reconciliation_system_design.py test in commit 6baef20d
(T-0958/T-0960/T-0962 drained that registry's deferrals). Applied the
same fix shape: `if not deferred: return` before the loop, with a
comment citing the precedent. No fake deferred entry was manufactured.

Mirroring that exact guard clause made this test 95% textually similar
to the three sibling registry-family tests (system_design,
supply_chain, evasion), which DUP001 correctly flagged as new. Waived
DUP001 on TestWeaknessesExhaustiveness with an honest reason (this is
the T-0384/T-0385/T-0386/T-0387/T-0388 family's established convention
of identical-shape positive-case tests per registry file; extracting a
shared helper across four independent test modules is a cross-file
refactor out of T-1116's declared scope) rather than widening scope to
do that extraction.

Evidence: tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
(pytest -q: 8/8 passed in the full module, collected node id recorded
via `frob ticket evidence`)

Filed: none

Gates: `uv run frob check --ticket T-1116 --budget 100` (chunked across
4 invocations covering gates-fast, gates-native, gates-security,
static/lint) -- clean, 0 errors. DUP001 (3 findings) waived per above,
reason recorded inline at the class anchor.

### Changed
```
 tests/test_registry_reconciliation_weaknesses.py | 10 ++++-
 tickets.md                                       | 54 +++++++++++++++++++++++-
 2 files changed, 62 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness::test_every_deferred_entry_targets_an_open_ticket` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
