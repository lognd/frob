## Done report

`_merge_main_into_worktree` (land's internal merge stage) already scoped
its own ledger splice to the landing ticket via `_splice_only_ticket`,
but the REGISTERED `tickets.md` git merge driver -- `frob ticket
merge-driver` -> `splice_ledger`, which fires on ANY `git merge`/`pull`/
`rebase` that touches the ledger and IS the mechanism git itself invokes
mid-`git merge --no-commit --no-ff` inside that same land stage -- still
resolved a same-id divergence via bare state-rank alone (`_newer`). A
stale copy can sit at a HIGHER rank than a richer one for free
(`queued`/`planned`/`in-progress` are all trivially reachable by
hand-editing or a requeue, but a Done report is only ever written once
real work is done), so a Done-report side sitting at a lower or tied
rank against a reportless side could still lose its report -- the field
incident landing T-0633/T-0637, where each merge stage regressed the
landing ticket's own block back toward main's bare state and forced a
manual `start`+commit repair before every land.

First-pass fix (round 1): `_newer` checked Done-report presence
unconditionally ahead of state-rank whenever neither side was terminal.
Reviewer REJECTED this on one finding: an unqualified "report always
wins" rule is itself buggy in the INVERSE direction -- a STALE Done
report left on a lower-rank block (e.g. a ticket requeued back down
without its old report body ever being stripped) would then beat a
genuinely more-advanced, reportless side, which is exactly the kind of
silent progress-loss this ticket exists to prevent, just pointed the
other way.

Round 2 fix (this report): `_newer` now applies a QUALIFIED rule, three
tiers checked in order:

1. TERMINAL SUPREMACY (unchanged from round 1): a `done`/`dropped` side
   always wins over a non-terminal side, Done report or not (T-0537's
   regression lock; the `test_close_fails_after_merge_when_main_dropped_
   same_id` race).
2. Between two NON-TERMINAL sides where Done-report presence DIFFERS:
   the reported side wins ONLY IF the reportless side does not STRICTLY
   outrank it. If the reportless side has a strictly higher state rank,
   rank wins instead. This closes BOTH directions: the original T-0682
   incident (reported side was in-progress vs main's bare queued -- the
   reported side is ALSO the higher-rank side, so it still wins) and the
   reviewer's inverse case (a stale queued+report side no longer beats a
   genuinely-advanced in-progress+no-report side).
3. Otherwise (Done-report presence is a wash), unchanged fallback to
   plain state-rank, tie-broken by `b` (theirs) as before.

Test changes in `TestSpliceLedgerRicherStatePreference` (splice_ledger
level): the round-1 tests that asserted the (now known-wrong) "report
wins even when the reportless side strictly outranks it" behavior were
replaced, not just added alongside, since that assertion no longer holds
under the qualified rule:

- `test_report_side_still_wins_when_it_also_outranks_the_reportless_side`
  -- the original field incident, unchanged conclusion: reported side is
  ALSO the higher-rank side (in-progress+report vs queued, no report) --
  still wins.
- `test_stale_report_on_lower_rank_still_loses_to_a_strictly_outranking_
  reportless_side` -- the new qualification's core case: a stale
  queued+report side loses to a strictly-outranking in-progress+no-report
  side.
- `test_stale_report_on_lower_rank_still_loses_regardless_of_which_side_
  it_is_on` -- same case, ours/theirs swapped, proving the qualification
  is symmetric.
- `test_neither_side_reporting_still_falls_back_to_state_rank` --
  untouched, still the T-0577/T-0537 non-regression guard.

`TestMergeMainIntoWorktreeRicherState`'s integration test was also
corrected to the non-inverted scenario (worktree in-progress+report,
which also outranks main's untouched queued/bare copy) so its assertion
matches the qualified rule rather than the rejected round-1 behavior.

Filed: none (all work stayed within scope: src/frob/tickets/_land.py,
tests/test_ticket_land.py).

### Changed
```
 src/frob/tickets/_land.py |  65 +++++++--
 tests/test_ticket_land.py | 184 +++++++++++++++++++++++++
 tickets.md                | 340 +++++++++++++++++++++++++++++++++++++++++++++-
 3 files changed, 572 insertions(+), 17 deletions(-)
```

### Evidence
(no evidence recorded)
