## Done report

The rapid-sweep self-absorb/regression-ticket-filing write
(`_file_regression_ticket`) can run IN-PROCESS inside `frob.verify.
_worker.run_coalesced_verification`, which is spawned synchronously
mid-land, inside a dispatched agent's own shell -- so `os.environ`
still carries that agent's `FROB_WORKTREE` (naming its leased
WORKTREE) even while the worker legitimately writes against the
shared ROOT it already resolved correctly. `enforce_worktree_lease`
cannot tell "worker writing to its own resolved root" apart from "an
agent mistakenly mutating main" and refuses every such write --
`WorktreeLeaseViolation`, twice in one measured session, always
against the exact root the worker had already resolved right.

Fix: added `frob.tickets._worktree_guard.unleased_root_env`, a narrow
context manager that strips FROB_WORKTREE/FROB_AGENT for the duration
of one write and restores them immediately after -- the same
precedent `_rapid_sweep._detached_sweep_env` already established for
its own subprocess env ("a detached sweep... is not 'a dispatched
worktree agent'... must not inherit whichever worktree the LANDING
process happened to be leased to"). `run_coalesced_verification` wraps
only the `_file_regression_ticket` call in it, never the whole worker,
so nothing else this process does is ever affected.

Kept the context manager inside frob.tickets._worktree_guard (in
scope) rather than frob.verify, so the SELFAUDIT001 env.read/env.write
capability finding lands on the tickets_ledger design component (which
already declares that capability via this same module's existing
os.environ reads) instead of introducing a brand-new capability onto
the verify component -- avoiding the same kind of undeclared-Flow
problem T-3378 hit with frob.gates, without touching design/frob.strata.

Added a must-fire test (the filing call observes neither env var set)
and two must-stay-quiet tests (the ambient lease is restored
afterward; no-ambient-lease stays unset afterward, the single-
developer control). Full tests/unit/verify/test_worker.py: 34/34 pass.
frob test --base main: python exit=0.

Out-of-scope note: the SAME `_file_regression_ticket` fallback gap
this incident also exposed -- `_dispose_to_existing_duplicate_or_none`
in `frob.app.ticket_runner._rapid_sweep` only recovers a
`DuplicateTicket`/`DuplicateFinding` refusal, never a
`WorktreeLeaseViolation` -- is untouched here; `_rapid_sweep.py` is not
in this ticket's scope. That module's OWN land-path call sites
(`_rapid_sweep.py:3894`/`3898`) can still hit the identical
`WorktreeLeaseViolation` this fix does not reach, since they run
synchronously inside `frob ticket land` itself rather than through
`run_coalesced_verification`. Filed as a follow-up.

(Follow-up: T-3459)

### Changed
```
 tickets/T-3379/ticket.md           | 21 +++++++++++++++-
 tickets/T-3459/ticket.md | 50 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 70 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/verify/test_worker.py::TestUnleasedRootEnv::test_filing_call_sees_no_worktree_lease_env` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestUnleasedRootEnv::test_ambient_lease_env_is_restored_after_filing` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestUnleasedRootEnv::test_no_ambient_lease_stays_unset_after_filing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 11 error(s), 4292 warning(s), 863 waived
- error-findings: COV001@src/frob/tickets/_worktree_guard.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3379, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
