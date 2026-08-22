## Done report

Post-merge refresh of the captured gate-state claim. The prior claim diverged on a single phantom finding -- rule id EMPTY, file 'tickets.md' -- which is the retired v1 monofile: it exists neither on disk nor in git ls-files, and is not a member of T-2666's declared scope. Refreshing so the recorded claim matches the measured tree; the phantom itself is filed separately as a land-blocking defect.

### Changed
```
 design/frob.strata                                 |  10 +-
 .../registry/capability-via-ratchet.lock.json      |   6 +-
 rapid-debt.jsonl                                   |   3 +
 .../unit/strata/test_sys107_via_scope_advisory.py  |  40 +++++++
 tickets/T-2666/done-report.md                      | 120 +++++++++++++++++++++
 tickets/T-2676/ticket.md                 |  60 +++++++++++
 6 files changed, 235 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/strata/test_sys107_via_scope_advisory.py::TestTestsuiteExecViaListRestored::test_testsuite_exec_has_no_via_less_sys107_finding` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 36 error(s), 947 warning(s), 698 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
