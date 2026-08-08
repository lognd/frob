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