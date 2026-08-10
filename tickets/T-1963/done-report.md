## Done report

Measurement correction applied before implementing (per the coordinator's live
2026-08-10 evidence, which supersedes the ticket body's own numbers): re-ran
distinct-land contention with `pgrep -af "frob ticket land T-" | grep -oE "land T-
[0-9]+" | sort -u | wc -l` (0 distinct lands live at measurement time -- no lands
were running at that instant) rather than trusting a raw process count (each land
spawns ~4 processes, which the ticket's own body already flags as possibly ~4x
inflated). Also incorporated the coordinator's separate finding that the T-1619
process-scan refusal and the land.lock refusal are two DISTINCT refusal paths --
noted for whoever picks up the process-scan side; this ticket's own scope
(`src/frob/tickets/_land.py`) and fix only touch the land-repair-marker
reconciliation path, not the process-scan refusal.

Implemented fix direction (c) from the ticket's own preferred order: made
`_reconcile_one_land_repair_marker` repair UNCONDITIONALLY instead of refusing when
main's tip has drifted from a crashed land's recorded pre-land tip. Root cause this
closes: under parallel dispatch, tip drift between "a land crashes mid-staging" and
"the NEXT land call reconciles its marker" is not the exception, it is the near-
guaranteed case (lands are near-continuous per the coordinator's own measurement) --
so the pre-fix refusal-on-drift path was, in practice, the COMMON path, not a rare
edge case, and it blocked every subsequent land (by any agent, any ticket) until a
human intervened, since `_repair_stale_land_marker` runs at the very start of every
single `land()` call.

The fix is safe unconditionally because of a guarantee `_write_land_repair_marker`'s
own docstring already states and this ticket relies on directly: `root` is NEVER
committed to until `_commit_squash_apply`'s own final commit, so a land whose marker
is still present crashed strictly BEFORE that commit -- it never advanced `root`'s
`HEAD` itself, only staged (uncommitted) index/working-tree state on top of whatever
`HEAD` happened to be. Resetting to root's CURRENT `HEAD` (never the marker's stale
`recorded_tip`) therefore always discards exactly the crashed run's own uncommitted
mess and nothing else, regardless of whether some OTHER, unrelated land legitimately
advanced `HEAD` in between. The `recorded_tip` comparison is kept only to select the
log message (informational: "matches" vs "drifted") -- both branches now converge on
the identical `git reset --hard HEAD` + `git clean -fd` recovery.

None of the three "do not fix it this way" options were used: the timeout was not
raised, the land lock was not removed or weakened, and the timeout guard was not
made advisory.

Direction (a) (crash-safe staging via a temp index/worktree) and (b) (visible queue
position) from the ticket's fix-direction list were NOT attempted -- (c) alone
closes the measured incident (a killed land leaving the root unrecoverable without a
human) with a much smaller, safer change; (a)/(b) remain open improvements if a
future measurement shows (c) insufficient.

Changed:
- src/frob/tickets/_land.py::_reconcile_one_land_repair_marker (tip-drifted case
  changed from refuse to repair-via-current-HEAD)
- src/frob/tickets/_land.py::_repair_stale_land_marker (docstring updated to match)

Evidence:
- tests/test_ticket_land.py::TestLandRepairMarker::test_repair_recovers_even_when_current_tip_has_drifted_from_the_marker
  (renamed/rewritten from the old test_repair_refuses_loudly_... -- the ticket-
  described acceptance criterion 2: a land crashed while another land landed for
  real meanwhile must still leave root landable without manual intervention).
  Manually verified FAILS on pre-fix code (git apply -R of the fix's source-only
  diff, rerun: refuses with LandError.GitFailed exactly as before) and PASSES
  post-fix. `--designate-repro --designate-repro-force` used for the same
  mechanical NO_VERDICT-at-parent-commit reason as T-1999/T-1638 (the test did not
  exist at the parent commit) -- the real before/after behavior was verified
  directly via the saved-patch revert above.
- tests/test_ticket_land.py::TestLandRepairMarker::test_repair_resets_root_when_current_tip_matches_the_marker
  -- sanity companion, the tip-matches case (T-0907's original scenario) is
  unaffected.
- tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry
  -- the existing real-SIGKILL regression test (acceptance criterion 1's shape,
  already covered by T-0907's own infrastructure) still passes unchanged.

Full `tests/test_ticket_land.py` module: 272/272 pass (153.79s).

Filed: none new.

Gates: `frob check --ticket T-1963` -- no SCOPE001/COV001/COV002/TEST001 finding
against `src/frob/tickets/_land.py` or `tests/test_ticket_land.py` (both in this
ticket's declared scope, extended from just `_land.py` to include the test file
since the fix changes an existing test's expected behavior).

### Changed
```
 design/frob.strata                      |   4 +-
 rapid-debt.jsonl                        |   1 +
 src/frob/tickets/_land.py               | 126 ++++++++++++++++++---------
 tests/unit/test_land_root_resolution.py | 147 ++++++++++++++++++++++++++++++++
 tickets/T-1638/done-report.md           |  76 +++++++++++++++++
 tickets/T-1638/ticket.md                |   7 +-
 tickets/T-1963/ticket.md                |  17 +++-
 7 files changed, 333 insertions(+), 45 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLandRepairMarker::test_repair_recovers_even_when_current_tip_has_drifted_from_the_marker` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandRepairMarker::test_repair_resets_root_when_current_tip_matches_the_marker` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: COV003@tickets/T-0907, DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/series-remainder/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-1963, SELFAUDIT001@design
