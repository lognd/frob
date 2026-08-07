## Done report

Churn item 2 (docs/audits/coordination-churn.md#2): when a worktree carries
several tickets, the first land's squash absorbs the siblings' files and
ledger state; each subsequent land stages an EMPTY squash and the final
commit exits 1 with no stderr, surfaced as a scary, unexplained
`CommitFailed` -- the coordinator then manually verifies state+content on
main every time (~8 occurrences).

`_land_squash_apply` now checks, right before attempting the landing
commit, whether the squash-apply staged nothing at all
(`_staged_files(root)` empty). If so, it verifies (never assumes) genuine
absorption via `_absorption_verified`: `final_id` must already be `done`
in `root`'s CURRENT ledger (loaded fresh, post-splice), AND every file in
the ticket's own `scope` must already match content-for-content between
the worktree's finalized HEAD and `root`'s current HEAD
(`_absorption_scoped_content_matches`, a direct cross-checkout `git diff`
since a worktree shares its object store with its primary checkout).
When both hold, `_report_stacked_sibling_absorption` returns a clean `Ok`
`LandReport` naming the ALREADY-EXISTING absorbing commit
(`commit_sha` = root's current HEAD, unchanged) with `ledger_spliced=False`
as the honest, reusable signal that nothing new was committed this call
(the frozen `LandReport` model could not gain a new field within this
ticket's scope). Verification failing for any reason falls through to the
original `_commit_squash_apply` attempt and its unmodified, honest
`CommitFailed` error -- an empty stage for some OTHER, unexplained reason
is never silently reported as success.

Exercised via the T-0795 idempotent-retry path (retrying `land()` for a
ticket whose FIRST attempt already fully succeeded is the same code shape
as a sibling absorbing a later ticket's squash -- both reach
`_land_squash_apply` with a worktree branch whose content and ledger
state are already fully present on `root`).

### Changed
```
 src/frob/tickets/_land.py | 131 +++++++++++++++++++++++++++++++++++++++++-----
 tests/test_ticket_land.py |  46 ++++++++++++++++
 tickets.md                |  52 +++++++++++++++++-
 3 files changed, 213 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_after_full_success_reports_absorption_not_commit_failed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_after_finalize_then_squash_failure_lands_the_diff` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_when_still_queued_re_runs_the_ordinary_transition` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 4898 warning(s), 322 waived
- error-findings: DOC001@docs/audits/coordination-churn.md
