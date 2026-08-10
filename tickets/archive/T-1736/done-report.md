## Done report

T-1736 wires frob.verify.record_intent into the land-commit path -- the
T-1686 epic's missing enqueue side. T-1687 built the durable verify-queue
foundation-only and T-1688's coalescing worker only drains/advances/
compacts an EXISTING queue; without this leaf nothing ever enqueued into
it, no matter how many lands happened.

_land_locked now calls _record_verify_intent_for_landed_commit once,
right after a REAL (non-dry-run) _land_squash_apply success -- never
from inside _land_squash_apply itself, which is outside this ticket's
own declared scope (src/frob/tickets/_land.py alone).

The commit's own diff is computed via frob.gitio.working_diff(root,
pre_land_tip): pre_land_tip is root's own tip captured before the
squash-apply started, a direct ancestor of the just-sealed commit, so
merge-base(HEAD, pre_land_tip) IS pre_land_tip and the resulting diff is
exactly this land's own delta, not some other window. The diff is
resolved against a frob.graph snapshot (load-or-build against the same
.frob/cache.db every other graph-backed caller shares) into a
touched-symbol set via a local span-overlap match
(_touched_symrefs_for_intent) -- a deliberate, disclosed frob:waive
DUP001 duplicate of frob.gates._touched_symrefs/_overlaps, since
src/frob/gates/__init__.py is outside this ticket's own scope too.

_record_verify_intent_for_landed_commit was split (ARCH001, 96 vs 60
lines) into itself plus _load_snapshot_for_intent and
_record_intent_or_log.

Best-effort throughout: a diff-compute failure, a graph-build failure,
an empty touched-symbol set, or a record_intent failure are each logged
(WARNING/INFO) and swallowed, never raised -- the land already succeeded
and sealed a real commit by the time this runs.

Disclosed out-of-scope finding: 5 tests/test_ticket_land.py tests fail
on a clean worktree at main tip, unrelated to this ticket's own change
(they fail in fixture SETUP, before land() is ever called) -- T-1758
made new_ticket auto-commit internally by default, and these 5 tests'
own _commit_all(wt, "wip"/"file...") call right after new_ticket now has
nothing left to stage. Filed as T-1829 rather than fixed here
(out of scope: src/frob/tickets/_new_renumber.py/test fixtures).

frob check --ticket T-1736: 0 errors (the one pre-existing unrelated
ARCH001 in src/frob/tickets/_new_renumber.py cleared once main's own
sibling lands caught up).
frob check --land-parity: clean, 0 unscoped errors.

### Changed
```
 docs/modules/tickets.md            |  31 ++++++
 src/frob/tickets/_land.py          | 168 ++++++++++++++++++++++++++++++-
 tests/test_ticket_land.py          | 198 +++++++++++++++++++++++++++++++++++--
 tickets/T-1686/ticket.md           |   4 +-
 tickets/T-1736/ticket.md           |  83 +++++++++++++++-
 tickets/T-1829/ticket.md |  23 +++++
 6 files changed, 495 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestTouchedSymrefsForIntent::test_overlapping_hunk_matches_the_symbol` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestTouchedSymrefsForIntent::test_non_overlapping_hunk_matches_nothing` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestTouchedSymrefsForIntent::test_different_file_matches_nothing` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRecordVerifyIntentForLandedCommit::test_dry_run_is_a_noop` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRecordVerifyIntentForLandedCommit::test_real_land_records_an_intent_entry` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRecordVerifyIntentForLandedCommit::test_no_resolvable_symbols_records_nothing` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRecordVerifyIntentForLandedCommit::test_diff_failure_is_logged_not_raised` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 5 error(s), 1255 warning(s), 738 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/tickets/_doable.py, ARCH103@src/frob/app/ticket_runner/_query.py, COV001@src/frob/tickets/_doable.py, PRE001@tickets/T-1736
