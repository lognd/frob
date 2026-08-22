## Done report

`frob ticket close` never promoted the `T-draft-*` follow-ups a ticket
filed the way `frob ticket land`'s own `_finalize_sibling_drafts` does.
Added `_promote_pending_drafts_after_close` (called right after `_close`'s
own successful state transition + ledger commit): loads the current
queue, promotes every remaining draft-id ticket via the same
`finalize_draft` primitive `frob ticket promote` uses (no worktree/main
split needed here -- `close` commits directly to `root`, unlike `land`).
A no-op when no drafts exist (silent, no new log noise). A promotion
failure is logged loudly by name with the exact hand-recovery command
and the process exits nonzero, since the ticket is already DONE by that
point and cannot be un-closed.

Changed:
- src/frob/app/ticket_runner/_close_cmd.py::_close (wired the new call
  after its ledger commit)
- src/frob/app/ticket_runner/_close_cmd.py::_promote_pending_drafts_after_close (new)

Evidence:
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_promotes_a_draft_the_ticket_filed
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_with_no_drafts_is_unchanged
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_reports_and_exits_nonzero_when_a_draft_cannot_be_promoted

Filed: none

Gates: frob check --ticket T-2738 --only gates-fast/gates-native/gates-security/lint/static
run individually (full unchunked run refused under FROB_AGENT); no new
errors attributable to this change -- the FMT001 line-length findings on
new frob:tests directive lines are fixed by land's own absorbed `frob fmt`
pass; all other findings (SCOPE002 under-capture warnings, repo-wide
gate:TICK/PRE/RENDER/LANG/PII/SELFAUDIT/WIRE/DRIFT/ARCH/DUP/PERF findings)
are pre-existing and unrelated to the touched files (verified by grepping
the full gates-fast/gates-native/gates-security output for this ticket's
two touched files -- only COV007/FMT001/SCOPE002 hits, all addressed or
pre-existing warnings).

### Changed
```
 tickets/T-2738/ticket.md | 20 +++++++++++++++++++-
 1 file changed, 19 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_promotes_a_draft_the_ticket_filed` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_with_no_drafts_is_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_reports_and_exits_nonzero_when_a_draft_cannot_be_promoted` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 48 error(s), 829 warning(s), 678 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_close_cmd.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DUP001@tests/unit/test_close_promote_drafts.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2738, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md, invalid-assignment@tests/unit/test_close_promote_drafts.py
