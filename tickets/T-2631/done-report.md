## Done report

Changed:
- tests/unit/test_lang_parse_guard.py::TestParseGuardIsWired.test_parse_source_calls_the_guard_helpers

Root cause: T-2575 split `_parse` (src/frob/lang/__init__.py) into `_parse`
plus a `_parse_uncached_and_store` tail to stay under ARCH001's line
threshold, moving the `_run_parse_with_timeout` call out of `_parse`'s own
source text. The guard is still reachable on every call (locked
behaviorally by TestParseGuardIsInvoked, unaffected) -- this is a stale
structural-lock test that assumed the guard call lived textually inside
`_parse`, not a real regression. The FIXTURE (test) was updated, not the
guard or the split.

Evidence: tests/unit/test_lang_parse_guard.py::TestParseGuardIsWired::test_parse_source_calls_the_guard_helpers
(designated repro, FAILED_AT_PARENT confirmed via --check-repro against
8ccaba2f967f7e82c5ff4d090040c35d33cdbedb)

Filed: none

Gates: uv run frob check --ticket T-2631 --only test -- clean for this
ticket's own scope (5 errors reported are all pre-existing, unrelated
findings on other files: DRIFT001 x3 on unrelated modules, TEST001 on
src/frob/strata/_multifile.py, claude-config-drift -- none touch
src/frob/lang/__init__.py or tests/unit/test_lang_parse_guard.py).
`frob check --land-parity` shows the same pre-existing repo-wide noise
from concurrent fleet activity, none scoped to this ticket's files.

### Changed
```
 tickets/T-2631/ticket.md | 8 ++++++--
 1 file changed, 6 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_lang_parse_guard.py::TestParseGuardIsWired::test_parse_source_calls_the_guard_helpers` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@scripts/fleet_status.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2631/src/frob/app/ticket_runner/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
