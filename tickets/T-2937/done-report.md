## Done report

Changed:
- src/frob/tickets/_leases.py::_rollback_pathspecs (new)
- src/frob/tickets/_leases.py::_land_check_with_optional_rollback (new)
- src/frob/tickets/_leases.py::_add_and_commit_tickets_md (wait_timeout_s/rollback_on_land_in_progress params)
- src/frob/tickets/_leases.py::commit_ticket_ledger_change (wait_timeout_s/rollback_on_land_in_progress params)
- src/frob/app/ticket_runner/_new.py::_commit_new_ticket_ledger_change_or_exit (new)
- src/frob/app/ticket_runner/_new.py::_new (uses the new helper + short bounded wait)
- docs/modules/tickets-landing.md (new section documenting the fix)

Evidence:
- tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_rollback_on_land_in_progress_leaves_root_clean (designated repro, FAILED_AT_PARENT confirmed against 0eff3a9c3)
- tests/test_ticket_leases.py::TestConcurrentNewTicketAllocationDuringLand::test_n_concurrent_new_ticket_calls_produce_distinct_ids (correctness proof: 8 concurrent `new_ticket()` calls with a real land.lock held throughout produce 8 distinct ids)

Root cause: `frob ticket new`'s CLI wrapper (`_new.py`) commits its ledger
write via `commit_ticket_ledger_change` with no `wait_timeout_s` override,
inheriting the full ~300-500s default `refuse_if_land_in_progress` wait
every other ledger-committing verb uses -- even though the ticket's id is
already durably, correctly allocated (`allocator_lock`/`ledger_lock`)
BEFORE that commit step ever runs. On timeout the pre-existing behavior
was `sys.exit(1)` with the ticket file still on disk, uncommitted --
already the DirtyMain hazard a long wait was implicitly trying to avoid.

Fix: `commit_ticket_ledger_change`/`_add_and_commit_tickets_md` now take
`wait_timeout_s`/`rollback_on_land_in_progress` (default to unchanged
behavior for every other caller). `_new()` passes a 20s bounded wait plus
`rollback_on_land_in_progress=True`: on `LandInProgress` specifically, the
just-written pathspecs are reverted/cleaned (`_rollback_pathspecs`)
before returning, leaving root exactly as clean as before the call.

Both directions proven:
- must-still-catch (id uniqueness): TestConcurrentNewTicketAllocationDuringLand,
  8 concurrent callers, real land.lock held, 8 distinct ids, zero DuplicateId.
- must-be-fast + must-not-strand-dirt: TestCommitTicketLedgerChange's new
  rollback test proves `git status --porcelain` is clean after a
  LandInProgress refusal under the short timeout.

A narrower fix scoping land's OWN lock to just its root-mutation window
(instead of the whole `_land_locked` body) was investigated and rejected
as out of scope -- `_land_lock` wraps land's entire precheck-through-
commit body in one process-wide flock; restructuring that is a high-risk
core-locking change to a file with a long incident history. This fix only
touches the `frob ticket new` call site's own wait/rollback behavior;
`start`/`close`/`drop`/`fail`/`requeue`/`evidence`/`done-report` are
unchanged (their ledger CHANGE, unlike a brand-new ticket's file, is not
safe to silently discard on timeout).

Filed: none new (this IS the filed bug ticket, findings recorded in its
own body at filing time).

Gates: `frob check --land-parity --ticket T-2937` clean of any
finding touching this ticket's files (CLAUDE001/COV004/CYCLE001/DOC006/
DOC008/TICK004/WIRE002 remaining in the unscoped list are pre-existing,
unrelated to this ticket's scope -- confirmed none reference
src/frob/tickets/_leases.py, src/frob/app/ticket_runner/_new.py, or
tests/test_ticket_leases.py). ruff-check/ruff-format/ty clean on all
touched files. ARCH001 long-function warnings this change newly
introduced (`_new`, `_add_and_commit_tickets_md`) were fixed by
extraction, not waived.

### Changed
```
 docs/modules/tickets-landing.md    |  58 ++++++++++++++
 src/frob/app/ticket_runner/_new.py |  60 +++++++++++---
 src/frob/tickets/_leases.py        | 155 ++++++++++++++++++++++++++++++++-----
 tests/test_ticket_leases.py        | 146 ++++++++++++++++++++++++++++++++++
 tickets/T-2924/ticket.md           |  23 ++++++
 tickets/T-2937/ticket.md | 148 +++++++++++++++++++++++++++++++++++
 6 files changed, 563 insertions(+), 27 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_rollback_on_land_in_progress_leaves_root_clean` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestConcurrentNewTicketAllocationDuringLand::test_n_concurrent_new_ticket_calls_produce_distinct_ids` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 21 error(s), 667 warning(s), 851 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC006@tickets/T-2923/ticket.md, DOC008@docs/commands/check.md, PRE001@tickets/T-2937, TICK004@tickets.md, WIRE002@src/frob/tickets/_unlanded.py
