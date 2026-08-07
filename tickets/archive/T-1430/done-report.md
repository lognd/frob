## Done report

T-1430: WIRE001's case 1 ("no non-test caller") cannot see the fourth
real-instance shape T-1428's brief named -- a new KEYWORD-ONLY PARAMETER
added to an EXISTING function's signature that no call site passes
(T-1384's own_obligations_clean, T-1399's gate_claims_verified, T-1391's
only_paths). The function itself already has a caller (it is not new), so
case 1's "no non-test caller" check never fires; the new parameter
specifically being unpassed is a narrower, signature-level question.

Fix: `_wire001_new_kwonly_param_violations` (src/frob/gates/_dead_symbols.py)
walks every function/method this diff TOUCHES but did not wholly define
(`_touched_callable_records`, the complement of case 1's `_new_callable_
records` proxy), reads the function's keyword-only parameter set from the
CURRENT working-tree source (stdlib `ast.parse`, exact for this one
question -- no need for `frob.lang`'s token-stream digest machinery here,
unlike T-1431's relocation check) and from the diff's merge-base
(`git show <base>:<path>`, same mechanism `_merge_base_body_match` already
uses), and flags any name present now but absent at the base for which
`_keyword_passed_outside_def` (a whole-tree `name=` keyword-argument text
scan, mirroring `_is_reached_outside_diff_tests`'s bias) finds no call
site anywhere.

No new rule id: this is WIRE001's existing rule id, case 4 of the same
gate -- no `_KNOWN_GATE_RULES`/registry change, no
`docs/design/registry/check-coverage.yaml` denominator bump (verified:
WIRE001/WIRE002 already carry their own `CHK-GATE-WIRE001`/`CHK-GATE-
WIRE002` registry entries from T-1428; this ticket adds no new gate/rule,
just a fourth detection case inside the same gate function).

Two regression tests added to `tests/test_gates.py::TestWireGate`:
- `test_new_kwonly_param_never_passed_is_flagged`
- `test_new_kwonly_param_passed_at_call_site_is_not_flagged`

Both use a real git repo fixture (same shape T-1431's tests use -- a real
commit for the pre-change baseline, then an uncommitted signature change
on a `work` branch) since the merge-base comparison needs a real sha to
`git show` against.

Scope: src/frob/gates/_dead_symbols.py, tests/test_gates.py -- both inside
T-1430's declared scope.

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py   |    68 +-
 src/frob/gates/_dead_symbols.py           |   251 +-
 tests/test_gates.py                       |   203 +
 tests/test_ticket_work_and_land_finish.py |    59 +
 tickets-archive.md                        | 20772 ++++++++++++++++++++--------
 tickets.md                                | 11349 ++-------------
 6 files changed, 17083 insertions(+), 15619 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestWireGate::test_new_kwonly_param_never_passed_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_new_kwonly_param_passed_at_call_site_is_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 9 error(s), 878 warning(s), 694 waived
- error-findings: AFFECT001@src/frob/gates/_dead_symbols.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/gates/_dead_symbols.py, COV003@tickets/T-1378, COV003@tickets/T-1406, COV003@tickets/T-1408, COV003@tickets/T-1419, COV003@tickets/T-1423, PERF004@src/frob/gates/_dead_symbols.py
