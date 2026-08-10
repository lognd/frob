## Done report

Extracted T-1841's retry-then-discard shape into a shared
`_commit_or_discard_ledger_write` helper in `_rapid_sweep.py`, and
routed the T-1983 auto-drop path (`_maybe_drop_resolved_ticket`)
through it alongside the existing regression-ticket path
(`_commit_regression_ticket`). On exhausted commit retries the
auto-drop path now restores the ticket file to its last-committed
state via `git checkout HEAD -- tickets/<id>/` (new
`_discard_uncommitted_ticket_drop`) instead of leaving the modified,
uncommitted `ticket.md` in the shared root -- closing the DirtyMain
deadlock and the duplicate-reason-line non-idempotency both traced to
this call site.

Both live call sites of `_maybe_drop_resolved_ticket` (T-1983's own
sweep-triggered path and T-2006's `doable`-triggered path,
`revalidate_dispatchable_sweep_tickets`) are fixed by this one change,
confirmed by reading both call sites directly.

First test (`TestCloseResolvedSweepTickets::test_commit_failure_
restores_root_to_clean_not_left_dirty`) was committed alone against
the unfixed code and watched to FAIL (a real AssertionError -- root
left dirty, ticket state left DROPPED) before the fix commit was
added; `--check-repro --base-ref <test-only commit>` independently
confirmed `FAILED_AT_PARENT`.

Filed as residue (not touched here, per the coordinator's explicit
split decision): T-2026 (a structurally different failure -- a DEAD,
interrupted process, fixed by a next-verb detection guard, not a
live-process discard) and T-2036 (a second, independent
defect in the same module: absolute-vs-relative path identity
mismatch silently drops a ticket whose findings are still live) and
T-2030 (the sweep writing into a concurrent agent's own worktree,
filed by another agent, root-resolution suspected as the shared
upstream cause of this and T-2036 -- not fixed in this
land, out of the verification budget available this session).

### Changed
```
 src/frob/app/ticket_runner/_rapid_sweep.py | 300 ++++++++++++++++++++++++-----
 tests/unit/test_rapid_sweep.py             | 275 ++++++++++++++++++++++++++
 tickets/T-2034/ticket.md         | 104 ++++++++++
 tickets/T-2036/ticket.md         |  83 ++++++++
 4 files changed, 717 insertions(+), 45 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_commit_failure_restores_root_to_clean_not_left_dirty` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_retry_after_commit_failure_does_not_duplicate_the_reason` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCommitOrDiscardLedgerWrite::test_returns_true_on_first_success` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCommitOrDiscardLedgerWrite::test_retries_then_succeeds` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCommitOrDiscardLedgerWrite::test_exhausted_retries_calls_discard_exactly_once_and_returns_false` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDiscardUncommittedTicketDrop::test_v2_store_restores_the_ticket_file_to_head` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDiscardUncommittedTicketDrop::test_v1_store_logs_and_leaves_root_alone` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, DRIFT002@src/frob/app/ticket_runner/_rapid_sweep.py, F401@/home/logan/projects/frob/.claude/worktrees/sweep-drop-fix/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/sweep-drop-fix/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-2034
