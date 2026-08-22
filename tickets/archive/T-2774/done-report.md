## Done report

Changed:
- src/frob/tickets/_land.py::_resolve_land_lock_wait_budget_s (new)
- src/frob/tickets/_land.py::_FROB_LAND_DEADLINE_ENV (new)
- src/frob/tickets/_land.py::land (call site now resolves the lock-wait
  budget from FROB_LAND_DEADLINE_S before acquiring _land_lock)
- docs/modules/tickets-landing.md (new section: "Declared land deadline
  bounds the lock wait, not a flat constant (T-2774)")
- tests/test_ticket_land.py::TestLandLockWaitBudgetFromDeclaredDeadline
  (5 new tests, both positive-control directions)

Evidence:
- tests/test_ticket_land.py::TestLandLockWaitBudgetFromDeclaredDeadline::test_no_declaration_keeps_the_flat_timeout_unchanged
  (BUG002 repro designated: FAILED_AT_PARENT against commit c1517f69f,
  the test-only commit before the fix)
- tests/test_ticket_land.py::TestLandLockWaitBudgetFromDeclaredDeadline::test_ample_deadline_derives_a_wait_budget_and_proceeds
- tests/test_ticket_land.py::TestLandLockWaitBudgetFromDeclaredDeadline::test_insufficient_deadline_refuses_immediately_with_no_lock_attempt
- tests/test_ticket_land.py::TestLandLockWaitBudgetFromDeclaredDeadline::test_short_wait_then_acquire_still_completes
- tests/test_ticket_land.py::TestLandLockWaitBudgetFromDeclaredDeadline::test_unparseable_deadline_falls_back_to_the_flat_timeout
- Existing tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout
  (6 tests) re-verified green, no regression.

Design notes:
- estimated_work_s is derived via
  frob.app._check_chunking._derive_post_land_sweep_budget_s (the SAME
  number land's own post-land sweep already budgets against, T-2715) --
  no second hardcoded estimate. Imported lazily, function-local, inside
  _resolve_land_lock_wait_budget_s, only when FROB_LAND_DEADLINE_S is
  actually set.
- Refusal reuses LandError.LandLockTimeout rather than minting a new
  ErrorSet member -- the ticket's own text explicitly allows this ("or a
  new, distinct variant"), and src/frob/tickets/_models.py (LandError's
  home) sits outside this ticket's declared scope and was leased by an
  unrelated in-progress ticket (T-2770) for the duration of this work.
  The caller-visible distinction the ticket actually requires (declined
  early vs died mid-land) is carried by a live typed Err plus a log line
  that explicitly says "declined-early ... NOT a died-mid-land timeout"
  and names the deadline/estimate, fired with zero elapsed wait and no
  holder probed -- a world apart from the bare, undiagnosable exit-143
  the 2026-08-21 incident produced.
- Absent FROB_LAND_DEADLINE_S, _resolve_land_lock_wait_budget_s returns
  Ok(_LAND_LOCK_TIMEOUT_S) unchanged -- no regression for any existing
  caller.

Positive controls proved (both directions, per the ticket):
- Insufficient declared deadline -> immediate Err(LandLockTimeout), zero
  lock attempts, no ticket-state mutation (test_insufficient_deadline_...).
- Ample declared deadline + free lock -> proceeds exactly as today, still
  yields a usable positive wait budget bounded by _LAND_LOCK_TIMEOUT_S
  (test_ample_deadline_derives_a_wait_budget_and_proceeds).
- Short wait then acquire with budget to spare still completes -- not
  every contended land is turned into a refusal
  (test_short_wait_then_acquire_still_completes).
- No FROB_LAND_DEADLINE_S declared -> behavior matches today exactly
  (test_no_declaration_keeps_the_flat_timeout_unchanged), and this is the
  case designated as the BUG002 repro.
- Malformed FROB_LAND_DEADLINE_S -> logged and treated as absent, does
  not brick landing (test_unparseable_deadline_falls_back_to_the_flat_timeout).

Filed: none (no new tickets needed; the frob.app._check_chunking cross-
component import is handled via a scoped, reasoned frob:waive SYS003 --
see that comment in _land.py for why relocating the derivation's
canonical home is a real architecture change out of this ticket's scope).

Gates: frob check --ticket T-2774 -- gate:SCOPE, gate:SYS (T-2774-owned
import), and every diff-driven check for this ticket's touched set are
clean; all remaining gate-summary errors are pre-existing repo-wide debt
unrelated to this change (verified by file/line: none reference
src/frob/tickets/_land.py's new code, tests/test_ticket_land.py's new
class, or the new docs section). frob test --base main: PASS, exit=0.

### Changed
```
 docs/modules/tickets-landing.md |  57 +++++++++++++++++
 src/frob/tickets/_land.py       | 127 +++++++++++++++++++++++++++++++++++++-
 tests/test_ticket_land.py       | 132 ++++++++++++++++++++++++++++++++++++++++
 tickets/T-2774/ticket.md        |  24 +++++++-
 4 files changed, 338 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLandLockWaitBudgetFromDeclaredDeadline::test_no_declaration_keeps_the_flat_timeout_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandLockWaitBudgetFromDeclaredDeadline::test_ample_deadline_derives_a_wait_budget_and_proceeds` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandLockWaitBudgetFromDeclaredDeadline::test_insufficient_deadline_refuses_immediately_with_no_lock_attempt` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandLockWaitBudgetFromDeclaredDeadline::test_short_wait_then_acquire_still_completes` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandLockWaitBudgetFromDeclaredDeadline::test_unparseable_deadline_falls_back_to_the_flat_timeout` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 19 error(s), 1276 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2202-mega-cluster.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2774/src/frob/tickets/_land.py, PERF004@src/frob/tickets/_evidence.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
