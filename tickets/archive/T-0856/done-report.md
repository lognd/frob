## Done report

Fixed the misattribution bug where land's evidence re-verify ran an entire
ticket's evidence ids as one pytest batch and, when any single id
failed/flaked, reported EVERY id in that batch as failed -- the T-0588
incident (36 evidence ids, one documented order-dependent xdist flake,
land wrongly reported all 36 as not-passing).

src/frob/app/ticket_runner.py's _verify_one_bucket_passing (called by
_verify_ids_passing, which both frob.tickets.land's injected passed
callable and frob ticket close/evidence's D-01 verification already
route through) still runs the WHOLE bucket as ONE batched run_selected
call first -- the cheap, common, all-green case is unchanged. Only when
that batched call executes but comes back not-ok (an actual test failure,
not an infra error) does it now fall back to a new helper,
_reverify_failing_bucket_individually, which reruns EACH id in that
bucket on its own via its own run_selected call, and returns only the
ids that individually failed as not-passing. A parallel helper,
_reverify_direct_pytest_individually, provides the same per-id fallback
for the separate no-[[test.runner]]-declared direct-pytest path
(_run_pytest_directly), so that fallback does not silently regress to
all-or-nothing misattribution either.

Both individual-rerun helpers consult frob.testing._stability.
quarantined_node_ids(load_stability(root)) (T-0575, read-only -- T-0635's
own wiring of stability into frob test proper is explicitly out of this
ticket's scope, not reimplemented here): an id that fails its own
individual rerun but is currently quarantined is still counted as
PASSING, so a documented flake cannot veto a land/evidence check. A
non-quarantined individual failure is still correctly excluded -- this is
attribution, not a blanket amnesty.

No changes were needed in src/frob/tickets/_land.py itself:
_reverify_evidence_post_merge already computes
`failing = [e for e in non_cmd if e not in passing_ids]` against
whatever `passing_ids` the injected `passed` callable returns, so once
ticket_runner.py's `passed` implementation attributes per-id correctly,
land's own refusal message already names only the genuinely-failing ids
with no further change. (_land.py stayed in the ticket's declared scope
per the brief, but the fix's actual surface area is entirely in
ticket_runner.py -- confirmed by tracing the call chain rather than
guessing.)

Mutant kill (hand-verified): changed
`elif item in quarantined:` to `elif False:` in
_reverify_failing_bucket_individually, reran
tests/unit/test_ticket_runner_land_release.py -- 1 test failed
(test_quarantined_failing_id_still_counts_as_passing, which asserts the
quarantined id is NOT vetoed), confirming the tests actually exercise the
quarantine-consultation branch. Reverted the mutant afterward and reran
the full file (13 passed) to confirm the tree is back to its real,
working state.

Evidence: 4 new node ids in tests/unit/test_ticket_runner_land_release.py
(TestReverifyFailingBucketIndividually's 3 tests plus
TestVerifyOneBucketPassingRoutesToIndividualReverify's 1 test), recorded
via frob ticket evidence.

Scope widened by one glob (recorded --reason-file justification):
tests/unit/test_ticket_runner_land_release.py, the existing precedent
file for ticket_runner CLI-wiring unit tests, for the new test classes.

Gates: uv run frob check --ticket T-0856 chunked over
lint/static/gates-fast/gates-native/gates-security. lint, static,
gates-native, and gates-security are all clean (0 errors). gates-fast
shows a larger set of pre-existing errors (32 COV002 + 8 SCOPE001) that
are NOT from this ticket's own work -- they all trace to T-0844 and
T-0854, the two prior tickets in this same worktree's serial chain,
both already closed and committed on this branch but not yet landed
onto shared main by the coordinator (T-0854 in particular added a whole
new module, src/frob/tickets/_live_tracker.py, plus a new test file --
every symbol in both shows up as COV002 now that T-0854 itself is
closed, i.e. no longer an OPEN ticket a frob:ticket edge could point
at). `frob check --ticket` diffs the full branch state against main, not
per-ticket commits, so both prior tickets' diffs stay visible and get
checked against T-0856's (the currently active ticket's) declared scope
until the coordinator lands them -- the documented T-0855 stacked-chain
hazard, not a T-0856 regression. Confirmed by re-running the exact same
chunk immediately after T-0854's own close (see T-0854's Done report):
the error count only grows as more of the chain's prior tickets remain
unlanded, never shrinks, and T-0856's OWN diff (src/frob/app/
ticket_runner.py + the one new test class) introduces zero new COV/SCOPE
findings of its own -- verified by diffing the error list against the
one recorded in T-0854's Done report and confirming every NEW line
traces to a src/frob/tickets/_live_tracker.py or
tests/test_tickets_live_tracker.py path (T-0854's own files), not
anything T-0856 touched.

Also noted: tests/test_ticket_land.py::TestClaimDivergencePostMerge::
test_unmeasured_fresh_check_skips_gate_reverification_land_proceeds failed
once when run as part of the ticket's full designated verify command
(alongside 5 other test files) but passed reliably every time it was run
alone or as part of just tests/test_ticket_land.py by itself -- a
pre-existing, order-dependent flake unrelated to this ticket's change
(the test never calls anything T-0856 touched; it injects its own
`passed=lambda ids: frozenset(ids)` callable directly). Not filed as a
new ticket since it did not reproduce on a second full run of the same
designated verify command and is already exactly the class of flake
frob.testing._stability's quarantine mechanism exists to track, not a new
finding.

### Changed
```
 docs/modules/tickets.md                       |  76 +++-
 src/frob/__main__.py                          |  14 +
 src/frob/app/config.py                        |   7 +
 src/frob/app/ticket_runner.py                 | 196 ++++++++-
 src/frob/gates/_mutation_evidence.py          |   9 +-
 src/frob/tickets/__init__.py                  | 106 ++++-
 src/frob/tickets/_land.py                     |  48 ++-
 src/frob/tickets/_live_tracker.py             | 264 ++++++++++++
 src/frob/tickets/_models.py                   |  23 +
 tests/test_evidence_integrity.py              |  54 +++
 tests/test_ticket_land.py                     | 338 ++++++++++++++-
 tests/test_tickets_live_tracker.py            | 310 ++++++++++++++
 tests/unit/test_ticket_runner_land_release.py | 104 +++++
 tickets.md                                    | 592 +++++++++++++++++++++++++-
 14 files changed, 2096 insertions(+), 45 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_land_release.py::TestReverifyFailingBucketIndividually::test_only_the_genuinely_failing_id_is_excluded` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestReverifyFailingBucketIndividually::test_quarantined_failing_id_still_counts_as_passing` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestReverifyFailingBucketIndividually::test_non_quarantined_failing_id_excluded` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestVerifyOneBucketPassingRoutesToIndividualReverify::test_batch_not_ok_falls_back_to_per_id_attribution` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
