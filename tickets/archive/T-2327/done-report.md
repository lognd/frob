## Done report

Updated tests/test_gates.py::TestDoc012CommandSectionGate.test_
undocumented_subcommand_fails to assert Severity.ERROR (was
Severity.WARN, stale since T-2299's promotion). Ran the full
TestDoc012CommandSectionGate class: 4/4 pass.

This closes the gap the must-fail fixture in
tests/test_doc012_promotion.py::TestDoc012PromotedToError was filed
against -- both files now agree the severity is ERROR.

### Changed
```
 docs/modules/gates.md              | 44 ++++++++++++++----
 rapid-debt.jsonl                   |  1 +
 src/frob/gates/_docblocks.py       | 28 ++++++------
 tests/test_doc012_promotion.py     | 93 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2299/done-report.md      | 52 +++++++++++++++++++++
 tickets/T-2299/ticket.md           | 37 +++++++++++++--
 tickets/T-2327/ticket.md | 55 ++++++++++++++++++++++
 7 files changed, 284 insertions(+), 26 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDoc012CommandSectionGate::test_undocumented_subcommand_fails` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fmt_directives.py, DRIFT002@scripts/fleet_status.py, DRIFT002@src/frob/verify/_drain.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2327, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md, WIRE003@docs/modules/cli.md
