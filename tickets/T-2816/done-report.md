## Done report

Changed:
- src/frob/tickets/_land._resolve_land_lock_wait_budget_s (T-2816: default in-land wait ceiling now near-zero)
- src/frob/tickets/_land._LAND_LOCK_DEFAULT_INLINE_WAIT_S (new constant, 10s)
- src/frob/tickets/_land._FROB_LAND_INLINE_WAIT_ENV (new opt-in env var, FROB_LAND_INLINE_WAIT_S)

Evidence:
- tests/test_ticket_land.py::TestLandLockInlineWaitDefaultsNearZero (5 node ids bound)
- existing TestLandLockWaitBudgetFromDeclaredDeadline suite re-verified passing unchanged (T-2774 non-regression)

Caller audit: `uv run frob explore xref land` shows the only production caller of
frob.tickets.land is frob.app.ticket_runner._land_cmd._land_core_invoke, reached
exclusively via the `frob ticket land` CLI, which the agent playbook always drives
as `wait_for_land_slot.py` (free external poll) then `timeout 540 frob ticket land`.
No hook, CI trigger, or non-interactive caller was found anywhere in the repo
(.claude/hooks/, scripts/, every import of frob.tickets.land). Decision: default
the in-land wait to near-zero (10s) rather than removing it outright, and add an
explicit FROB_LAND_INLINE_WAIT_S opt-in for a hypothetical future caller that
cannot poll externally, since none exists today but removing the capability
structurally was not asked for and costs nothing to keep as an escape hatch.

Proved both directions:
- test_ample_deadline_defaults_to_the_near_zero_ceiling_not_the_flat_500s: ample
  deadline + no opt-in resolves to 10s, not up to 500s.
- test_held_lock_released_quickly_leaves_almost_the_whole_deadline_for_work: a
  REAL held lock (planted via a holder thread) is waited out and released within
  the near-zero ceiling, proving budget remaining when work begins stays large.
- test_short_wait_then_acquire_still_completes (T-2774, re-verified): a land that
  waits briefly then acquires still completes -- not turned into a blanket refusal.
- test_insufficient_deadline_refuses_immediately_with_no_lock_attempt (T-2774,
  re-verified): a deadline that cannot cover estimated work alone still declines
  immediately with Err(LandError.LandLockTimeout) -- T-2774's core contract intact.
- test_opt_in_env_is_still_capped_by_the_remaining_budget: the opt-in cannot be
  used to reintroduce the SIGKILL case -- still capped by remaining budget.

Filed: none

Gates: uv run frob check --ticket T-2816 -- no error-level finding in any gate
attributes to src/frob/tickets/_land.py, tests/test_ticket_land.py, or
docs/modules/tickets-landing.md; all failing gates are pre-existing repo-wide
baseline noise unrelated to this change (verified by grepping gate output for
these three paths). ruff-format flagged both touched files as needing
reformatting -- left for frob ticket land's own absorbed fmt step per the
agent playbook (section 0 item 5), not hand-run to avoid drifting from that
step's canonical formatting pass.

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_land.py::TestLandLockInlineWaitDefaultsNearZero::test_ample_deadline_defaults_to_the_near_zero_ceiling_not_the_flat_500s` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandLockInlineWaitDefaultsNearZero::test_opt_in_env_restores_a_longer_in_land_wait` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandLockInlineWaitDefaultsNearZero::test_opt_in_env_is_still_capped_by_the_remaining_budget` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandLockInlineWaitDefaultsNearZero::test_unparseable_inline_wait_env_falls_back_to_the_near_zero_default` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandLockInlineWaitDefaultsNearZero::test_held_lock_released_quickly_leaves_almost_the_whole_deadline_for_work` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 22 error(s), 1294 warning(s), 717 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2790-check-stage-profile.md, DOC001@docs/investigations/T-2796-backlog-reproduction.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, LANG004@src/frob/lang/_support.py, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
