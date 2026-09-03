## Done report

The SYS111 capability-ratchet growth ratchet on core::fs.read (34->35, after
T-3416/T-3409/T-3429/T-3430 each added a genuine site) is fixed by
re-baselining docs/design/registry/capability-via-ratchet.lock.json's
accepted_count with a recorded reason, per the sanctioned "re-baseline, do
not waive" resolution.

Four sibling testsuite::* pairs (env.read 16->17, exec 224->225->226,
fs.read 171->172, fs.write 405->407) were also above ceiling when this
ticket started, unrelated pre-existing accumulated growth measured
alongside the core breach -- bumped the same way, following the T-2743
precedent already established in this same lock file for exactly this
class of finding.

BLOCKED-then-unblocked: test_sys_gate_zero_violations also requires 0 SYS100
violations, and 10 pre-existing SYS100 findings (tests/unit/test_check_
admission.py's undeclared exec sites) were a separate, unrelated defect
blocking the same shared test -- out of this ticket's scope, so filed T-3450
and blocked this ticket on it rather than force-closing against a red
acceptance test. T-3450 landed at a58cacf5d656db852617e2d2dd132f019b77cac0;
merged main into this worktree, re-measured (T-3450's own via-list addition
bumped testsuite::exec's true count to 226, one more than this ticket's
earlier bump assumed), corrected the ceiling to 226, unblocked, and
re-verified: test_sys_gate_zero_violations now passes green.

### Changed
```
 .../registry/capability-via-ratchet.lock.json      | 30 +++++++++++-----------
 tickets/T-3447/ticket.md                           |  7 +++--
 2 files changed, 20 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 13 error(s), 4206 warning(s), 856 waived
- error-findings: COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DOC007@tests/unit/test_main_entry.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, DRIFT002@tests/unit/test_main_entry.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3447, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
