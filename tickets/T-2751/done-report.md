## Done report

T-2738's close-time draft-promotion scan used `load_queue`'s merged
active+archive view without filtering by ticket state, so an
already-terminal DROPPED draft-id ticket (a stale leftover from a past
land, dropped as dead residue but never renamed off its draft id) was
attempted for promotion by ANY unrelated close -- reproduced live while
closing T-2737 in this exact series: the close itself succeeded, but the
promote pass then failed loudly on an ancient, unrelated dropped draft
and left worktree debris.

Fix: the draft scan now excludes tickets already in a terminal state
(DONE/DROPPED) -- only a genuinely pending (non-terminal) draft is
attempted.

Changed:
- src/frob/app/ticket_runner/_close_cmd.py::_promote_pending_drafts_after_close

Evidence:
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_promotes_a_draft_the_ticket_filed
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_ignores_an_already_dropped_draft
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_with_no_drafts_is_unchanged

Filed: none

Gates: scoped ruff-check/ty on the two touched files both clean; full
tests/unit/test_close_promote_drafts.py suite (5 tests) passes.

### Changed
```
 src/frob/app/ticket_runner/_close_cmd.py | 16 ++++++--
 tests/unit/test_close_promote_drafts.py  | 33 +++++++++++++++++
 tickets/T-2737/ticket.md                 |  2 +-
 tickets/T-2751/ticket.md       | 63 ++++++++++++++++++++++++++++++++
 4 files changed, 110 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_promotes_a_draft_the_ticket_filed` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_ignores_an_already_dropped_draft` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_with_no_drafts_is_unchanged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 39 error(s), 826 warning(s), 695 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_close_cmd.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2742/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@src/frob/tickets/_land.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@src/frob/serve/_socketd.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
