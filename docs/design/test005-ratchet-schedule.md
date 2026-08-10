# TEST005 floor ratchet-up schedule: 75/70 is a waypoint (T-1315)

`frob.toml`'s `[testing]` table carries the actual, gate-enforced
TEST005/TEST006 floors (`unit_branch_cov`, `module_line_cov`). This
document is the schedule that explains WHY those two numbers move over
time and WHEN the next move is due -- it does not duplicate them, and it
is not itself the mechanism: the mechanism is the numbers in `frob.toml`
plus a real, closeable ticket per step (never a comment nobody enforces).

## Extending, not contradicting, the T-0969 recalibration

T-0969 (2026-07-29) reset the floor from the aspirational 90/85 down to
75/70 because a fresh full-suite run at 90/85, measured on HONEST
post-attribution-fix data (T-1235 fixed subprocess + pool-worker coverage
recording), showed 1352 findings -- an unusable, un-triageable number
that was mostly noise (dominated by error-branch gaps on otherwise
main-path-tested code) rather than signal. 75/70 was chosen as the floor
where the *signal* (per-package findings worth fixing) was tractable.

T-0969's own in-file rationale comment already says this explicitly: the
TEST005 burn-down campaign "raises these back toward 90/85 as packages
come clean." This document is that promise made concrete -- 75/70 is the
WAYPOINT the recalibration always intended, not a new resting floor. A
floor that never moves again is not a recalibration, it is a surrender
(this ticket's own title).

## Current measured state (2026-08-08, this ticket's own measurement)

Two independent signals, both consulted rather than assumed:

1. **Epic closure.** `frob ticket epic T-1273` -- the per-package
   burn-down epic this ratchet ticket is itself a child of -- shows all
   38 children (T-1276..T-1313, one per top-level package) archived as
   `done`. Every one of those tickets' own acceptance criteria required
   its package to reach ZERO TEST005 findings at the then-current 75/70
   floor before closing. As of this date, the entire per-package
   burn-down this epic covers is complete.
2. **`frob-coverage.lock.json` (committed, last stamped 2026-08-06,
   commit `ada33703f`)** -- 2 days stale relative to this ticket's own
   base commit, the best available committed signal since this ticket
   cannot run `make coverage` itself (that is explicitly a
   COORDINATOR-only step, `docs/guides/agent-playbook.md` section 6b --
   a dispatched sub-agent must never attempt a full-suite coverage run).
   Its `module_line` map, queried directly rather than assumed:

   | floor | modules below it (of 477) |
   |------:|---------------------------:|
   |   70% | 8 |
   |   75% | 13 |
   |   80% | 22 |
   |   85% | 46 |
   |   90% | 102 |

Reading these together: the epic being fully closed at 75/70 is
consistent with the lock showing only 8 modules below 70% -- those 8 are
either drift since each package's own closure (new code landed after
that package's ticket closed, not yet re-covered) or module-line-level
gaps TEST005's SYMBOL-level check does not itself flag (a module's
average line coverage and a specific symbol's branch coverage are
different measurements; `docs/modules/gates.md` documents the
TEST005/TEST006 split). Either way, the honest conclusion from a
2-day-stale, sub-agent-only measurement is: **75/70 is very likely
already clear repo-wide, but this document does not assert that as
fact** -- the trigger for step 1 (below) is exactly the fresh
measurement that would confirm or refute it, run by whoever is not
bound by the coordinator-only restriction.

## The schedule

Four floors, each one step above the last, ending back at the original
90/85 aspirational target T-0969 stepped down from:

| step | unit_branch_cov | module_line_cov | status |
|-----:|-----------------:|------------------:|--------|
| 0 (current) | 75 | 70 | ACTIVE (`frob.toml` today) |
| 1 | 80 | 75 | tracked ticket, not yet triggered |
| 2 | 85 | 80 | filed by step 1's own Done report |
| 3 (target) | 90 | 85 | filed by step 2's own Done report |

Only step 1 is filed now, by this ticket -- steps 2 and 3 are filed by
their own predecessor's Done report at the point it closes, per the
"residue re-filed as real work becomes concrete" convention this repo
already uses everywhere else (`docs/guides/agent-playbook.md` section 0
item 8). Pre-filing all four now would just be guessing at trigger
numbers three measurements in the future; each step's own trigger can
only be evaluated honestly once the previous step has actually landed.

### Trigger, identical shape for every step

A step from floor `(B, M)` to `(B', M')` is DUE the moment ALL of the
following hold, checked by whoever owns that step's ticket (a
coordinator, since step 1 below requires the coordinator-only `make
coverage`):

1. A FRESH `make coverage` run (never a sub-agent's own scoped `pytest
   --cov`, per `docs/guides/agent-playbook.md` section 6c -- a scoped run
   cannot honestly measure the whole repo) followed by `frob check
   --stamp-coverage`, producing a current `frob-coverage.lock.json`.
2. `frob check --only test` at the CURRENT floor `(B, M)` reports ZERO
   TEST005 findings against that fresh measurement -- the floor is
   genuinely clear, not just believed clear.
3. The fresh `frob-coverage.lock.json`'s `module_line` map shows ZERO
   modules below the NEXT floor `M'` -- bumping `module_line_cov` to `M'`
   would create no new red. (`unit_branch_cov`'s own per-symbol data is
   not committed anywhere as durably as the module-line lock is; TEST005
   itself, step 2 above, is the check that actually enforces the branch
   floor once bumped -- this condition is a pre-flight sanity check, not
   a substitute for running the gate.)

If the trigger does not hold, the step's ticket stays queued/blocked --
never forced by lowering the bar to make the numbers fit anything less
than a real, fresh, repo-wide measurement.

### Action once a step's trigger holds

1. Bump `frob.toml [testing]`'s `unit_branch_cov`/`module_line_cov` to
   the step's new values -- this is the actual enforcement point; from
   the moment this commit lands, EVERY `frob check`/TEST005/TEST006 run
   anywhere reads the new floor, no separate code path needed.
2. Extend (never replace) the `[testing]` rationale comment with this
   step's own date and the measurement that justified it -- the same
   discipline T-0969's original comment and this document's own opening
   section both already follow: every number in `frob.toml` has a
   dated, cited reason attached, not a bare literal.
3. File the NEXT step's ticket (same body shape as this document's own
   step-1 ticket) before closing this one -- the schedule is only a
   living schedule, not a one-time comment, if each landed step produces
   its own successor.

## Why a per-package override table was NOT built

T-1315's own acceptance text offers two shapes: "per-package floor
overrides" or "a documented schedule/policy the gate reads." This
document chooses the schedule shape, for a concrete, checked reason: a
per-package override table would need a NEW field on `TestPolicy`
(`src/frob/gates/_models.py`) and new read/apply logic in the TEST005/
TEST006 gate bodies (`src/frob/gates/__init__.py`) -- real code, outside
this ticket's own declared scope (`frob.toml`,
`docs/design/test005-ratchet-schedule.md` only), and a second
enforcement mechanism to keep in sync with the first. It is also
unnecessary: the coverage LOCK's own per-module ratchet (`frob.toml`'s
existing rationale comment: "the coverage lock's per-module ratchet
prevents regression below current reality") already gives every
individual module a monotonic floor at its OWN best-ever recorded
percentage, regardless of the GLOBAL `[testing]` numbers -- a module that
has already reached 92% cannot regress below 92% today, with zero new
code, because `_apply_lock_ratchet` (`src/frob/gates/_coverage.py`)
already refuses to record a lower value once a higher one is committed.
The global floor and the per-module lock are two DIFFERENT, already-
existing mechanisms doing two different jobs -- this document's schedule
only needs to move the first one; the second was never the gap.

## What this document is not

It is not a claim that TEST005 is at zero right now -- see "Current
measured state" above, which is explicit about what could and could not
be verified from a sub-agent context. It is not a code change -- no gate
reads this document; the gate reads `frob.toml`. It is not permission to
bump the floor without measuring -- every step's trigger requires a
FRESH, real measurement, never a carried-forward assumption.
