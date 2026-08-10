---
id: T-1804
title: Deferred post-land sweep files spurious PRE001/SCOPE001 regression tickets
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestUnscopedErrorFindingsExcludesNoTicketNoise::test_pre001_and_scope001_are_excluded_but_real_findings_survive
- tests/test_ticket_land.py::TestUnscopedErrorFindingsExcludesNoTicketNoise::test_only_no_ticket_noise_present_returns_empty_not_none
designated_repro_test: null
threat: null
component: null
---
The deferred post-land sweep (`frob.app.ticket_runner._rapid_sweep.
run_deferred_post_land_sweep`) files a bug ticket for any "new" error
finding vs its rolling baseline. Measured today: five sweep-filed
tickets in one hour whose only findings were PRE001 and SCOPE001, all
dropped by the coordinator as noise.

ROOT CAUSE, confirmed directly: both rules are `_no_active_ticket_
violation`'s own B9 mechanism (`src/frob/gates/__init__.py`) -- a LOUD,
by-design error whenever a diff touches non-ledger source and no
`--ticket`/`T-####-`-prefixed branch is derivable. The sweep spawns
`frob check --budget N --json` with NO `--ticket` (deliberately, so it
can catch residue outside any one ticket's own scope -- see
`_unscoped_error_findings`'s own docstring). The sweep runs DETACHED,
against the SHARED root checkout, seconds to minutes after a land
returns -- and root can be, and regularly is, caught mid-dirt from a
DIFFERENT concurrent land (an untracked ticket directory, a staged-but-
uncommitted file) at exactly the moment the sweep's child process reads
its diff. `working_diff`'s own untracked-file inclusion
(`_untracked_hunks`, `git ls-files --others`) means this transient dirt
IS a non-empty diff to B9, and B9 fires exactly as designed: loudly,
unconditionally, whenever no ticket is derivable. Reproduced directly:
a bare `frob check` on a genuinely clean, HEAD-equals-main tree emits
0 findings (confirmed: `working_diff` reports 0 hunks); the false
positive is entirely a function of transient root dirt the sweep's own
detached timing exposes it to.

This is a DIFFERENT symptom of the same disease T-1699 targets
(DirtyMain misreading coordinator-owned dirt), but the fix belongs here
too: PRE001/SCOPE001 in this specific "unscoped, no ticket derivable"
mode are structurally never a real code regression signal for a
deferred sweep or `--land-parity` run (both explicitly, deliberately
pass no `--ticket`) -- they are a hygiene signal about root's git state
at the instant of measurement, which T-1699 is the right place to fix
at the source. Filing this as its own ticket rather than folding into
T-1699 because the REMEDY here is narrower and independent: exclude
these two rule ids from the sweep/land-parity's own comparison set,
which is correct regardless of whether T-1699 also reduces how often
root is transiently dirty.

Checked whether any OTHER rule shares B9's exact "always fires
unscoped+no-ticket" shape (`_no_active_ticket_violation`'s only two
callers, `src/frob/gates/__init__.py`): none. SCOPE001 and PRE001 are
the whole set.

FIX: `_unscoped_error_findings` (`src/frob/app/ticket_runner/
_land_cmd.py`), the single shared function both the deferred sweep
(`run_deferred_post_land_sweep`) and `--land-parity`
(`land_parity_findings`) call for their unscoped, no-ticket check, must
exclude PRE001/SCOPE001 from the returned finding-identity set --
reusing the existing `SCOPED_RUN_FLAKY_RULE_IDS`-style exclusion
precedent (`frob.gates._waive`), not a new one-off filter that could
drift out of sync with it.

## Done report

Root-caused and fixed the deferred post-land sweep filing spurious
regression tickets for PRE001/SCOPE001-only findings (5 in the last
hour, all dropped as noise by the coordinator).

Cause: `_unscoped_error_findings` (`src/frob/app/ticket_runner/
_land_cmd.py`), shared by the deferred sweep
(`run_deferred_post_land_sweep`) and `--land-parity`
(`land_parity_findings`), deliberately spawns `frob check --json` with
NO `--ticket` -- the whole point of the unscoped sweep is catching
residue outside any one ticket's own scope. `_no_active_ticket_
violation` (B9, `frob.gates.__init__`) fires PRE001/SCOPE001
unconditionally whenever such a run's diff touches any non-ledger file
with no derivable ticket -- by design, since this closed a real silent-
skip escape (T-0541). The sweep runs DETACHED against the SHARED root
checkout, seconds to minutes after its own land returns; by the time its
child process reads root's diff, a DIFFERENT concurrent land can have
left transient dirt there (an untracked ticket directory, a staged-but-
uncommitted file) -- `working_diff`'s own untracked-file inclusion
(`_untracked_hunks`) makes that dirt a non-empty diff, and B9 fires
exactly as designed for a hygiene condition the sweep was never built to
measure.

Confirmed directly: a bare `frob check` against a genuinely clean tree
(HEAD == main, working_diff computed 0 hunks) produces 0 findings --
the false positive is entirely a function of transient root dirt this
detached timing exposes the sweep to, not a defect in B9 itself.

Checked for a second such rule (coordinator's own request): B9's
`_no_active_ticket_violation` has exactly two callers in `frob.gates.
__init__` (`jobs["scope"]`, `jobs["prework"]`) -- SCOPE001 and PRE001
are the whole set. No other rule shares this "always fires unscoped +
no ticket" shape.

Fix: `_unscoped_error_findings` now excludes
`_UNSCOPED_NO_TICKET_STRUCTURAL_NOISE_RULE_IDS` (PRE001, SCOPE001) from
its returned finding-identity set -- fixing BOTH the deferred sweep and
`--land-parity` in the one shared function, rather than patching the
sweep alone and leaving land-parity exposed to the identical false
positive. A run whose only findings were this noise now reads as a
real, measured EMPTY set (clean, matches baseline), not `None`
(unmeasurable) -- tested explicitly
(`test_only_no_ticket_noise_present_returns_empty_not_none`) so a
future change cannot silently regress "excluded" back into "skip the
whole comparison".

This is a narrower, independent fix from T-1699 (DirtyMain's own
misreading of coordinator-owned root dirt): T-1699 is the right place
to reduce HOW OFTEN root is transiently dirty; this ticket is the right
place to stop that transient dirt from ever reaching the sweep's
regression-comparison logic as a false "new code defect" in the first
place. Both are needed; neither substitutes for the other.

No root-cause fix needed under DEAD001/WIRE001/OPAQUE001/REF002: the
new constant and its two call sites are reachable from
`_unscoped_error_findings`'s own two real callers plus the two new
tests; nothing dead, unwired, opaque, or under-referenced was added.

### Changed
```
 tickets/T-1804/ticket.md | 76 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 76 insertions(+)
```

### Evidence
- `tests/test_ticket_land.py::TestUnscopedErrorFindingsExcludesNoTicketNoise::test_pre001_and_scope001_are_excluded_but_real_findings_survive` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUnscopedErrorFindingsExcludesNoTicketNoise::test_only_no_ticket_noise_present_returns_empty_not_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 804 warning(s), 727 waived
- error-findings: none (measured, zero errors)
