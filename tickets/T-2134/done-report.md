## Done report

Investigated whether the v1 `tickets.md` monofile is still live anywhere
(code, config, gate logic) since the v2 sharded-ticket migration.

Finding: the physical `tickets.md`/`tickets-archive.md` files were already
deleted by T-2356 (commit e2ed60480, landed 2026-08-17), which also added
a guard (`test_v2_mode_repo_with_a_lingering_monofile_errors`) that ERRORs
if either monofile is ever resurrected in a v2-mode repo. Confirmed on
this branch: `tickets.md` is absent from the worktree and from
`git ls-files`; `frob check --ticket T-2134` (scope=['tickets.md']) shows
zero findings against the bare `tickets.md` path (grepped the full run:
no hits outside `docs/modules/tickets*.md`, which are separate, real doc
files, not the retired ledger). T-2134's original 10 DOC006 findings are
already gone as a byproduct of T-2356's land.

`LEDGER_PATH`/`_LEDGER_NAME` ("tickets.md") remain as live constants in
`src/frob/tickets/_models.py`/`_store.py`, used only as a scope-matching
glob literal (the "always in scope" pattern, T-0241) and as
`ledger_path()`'s target -- harmless: the glob matches nothing since no
file has that name post-T-2356, and `ledger_path()`'s only remaining
callers are legacy-format test fixtures (tests/test_evidence_integrity.py,
tests/test_gates_tick005.py) that construct a v1-shaped repo on purpose.

Real live defect found and NOT fixed here (out of this ticket's
`tickets.md`-only scope): `frob.check._python._gates_error_result`
hardcodes a `Diagnostic(file="tickets.md", ...)` with no `code=` set,
emitted whenever `GateError.QueueUnavailable` fires for ANY ledger-v2
queue-load failure (a malformed ticket dir, or -- per
`_tick001_duplicate_ids`'s own docstring -- a duplicate id across active/
archive). This manufactures an empty-rule-id finding against a path that
cannot exist in this repo any more, and is the exact symptom described in
this ticket's dispatch brief (a `frob ticket land` blocked twice by a
ClaimDivergence citing an empty-rule-id finding against `tickets.md`,
whose real cause was a corrupt ledger). Filed as a follow-up bug ticket
with full root-cause detail (draft id below; real id after land).

No code change was warranted for T-2134 itself: the file is already gone,
its own findings are already gone, and the one remaining live defect this
investigation surfaced needs a separate scope (src/frob/check/_python.py)
this ticket does not declare.

Changed: none (investigation-only; confirmed pre-existing T-2356 fix
already resolved this ticket's stated symptom)
Evidence: tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_with_a_lingering_monofile_errors, tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_is_silent
Filed: T-draft-f3bbfd8e (gates: QueueUnavailable manufactures an
empty-rule-id finding against the retired tickets.md path -- real id
after land)

### Changed
```
 tickets/T-2134/ticket.md           |  7 ++-
 tickets/T-draft-f3bbfd8e/ticket.md | 92 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 98 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 37 error(s), 725 warning(s), 697 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-draft-f3bbfd8e/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
