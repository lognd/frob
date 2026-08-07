## Done report

T-0835's own ledger start was already recorded via `frob ticket start`; this
report documents the actual implementation.

`frob ticket start` now refuses two cases that previously succeeded silently
and caused the 5.5h double-dispatch incident:

1. Terminal state (done/dropped): `_refuse_if_terminal` in
   `frob.app.ticket_runner` exits 1 before any transition is attempted,
   naming the landing commit (`git log --grep "land <id>"`, matching this
   repo's own `frob ticket land` commit-message convention) when the ticket
   is DONE and one is cheaply findable, or just the terminal state
   otherwise (including DROPPED, which never has a landing commit).

2. Foreign live lease: `_refuse_if_foreign_live_lease` reads every recorded
   lease via the existing `frob.tickets._leases.read_all_leases`, and
   refuses if the ticket's lease is pinned to a worktree other than the
   invoking one AND is not TTL-expired (`is_lease_ttl_expired`). A lease
   pinned to the SAME worktree is treated as idempotent (no refusal) so a
   restart after an interrupted session keeps working, matching the
   existing recovery path. `--steal` (new `AppConfig.ticket_steal` /
   `--steal` CLI flag) overrides this refusal only; it does not itself
   rewrite the lease file -- the existing `transition(..., IN_PROGRESS)`
   call already re-`record_lease`s pinned to the invoking worktree as part
   of its normal T-0473 sync, which overwrites the stolen worktree's lease
   file in place. That means the losing worktree's own later
   `resolve_lease`/`ticket_lease_pin` call (the same primitive `frob check
   --ticket`'s pin gate and any close/land preflight already depend on)
   fails against the new content -- no parallel invalidation mechanism was
   built, the existing one is simply reused as instructed.

Both checks run BEFORE the pre-existing "already in-progress" state check,
since either can be true while this worktree's own local ledger view still
shows an earlier state (exactly what let T-0806's second agent slip past
before this ticket).

Scope was widened by two files (`src/frob/__main__.py`,
`src/frob/app/config.py`) beyond the ticket's original four, via `frob
ticket scope --add --reason-file` before touching either -- the `--steal`
flag necessarily needs one `add_argument` call and one `AppConfig` bool
field/passthrough-allowlist entry, the same wiring every other ticket-start
flag (`--foreground`) already goes through. No other change was made in
either file.

Tests (tests/test_ticket_leases.py, real git fixture repos/worktrees, real
lease files, no lease-layer mocking):
- TestRefusesTerminalState: done (with landing-commit naming) and dropped.
- TestRefusesForeignLiveLease: refuses a live foreign lease (naming
  worktree + age + --steal); an expired foreign lease does not block;
  same-worktree restart after a requeue stays idempotent.
- TestStealOverride: --steal succeeds and invalidates the other worktree's
  lease (verified via `resolve_lease`, the same primitive `ticket_lease_
  pin`/`frob check --ticket` already depends on).
- TestDoubleDispatchIncidentRegression: the full T-0835 incident shape end
  to end -- A leases+works, B's plain start refused, B --steal succeeds, A's
  own lease resolution subsequently fails.

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_leases.py::TestRefusesTerminalState::test_refuses_done_ticket` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRefusesTerminalState::test_refuses_dropped_ticket` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRefusesForeignLiveLease::test_refuses_live_lease_in_another_worktree` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRefusesForeignLiveLease::test_expired_lease_in_another_worktree_does_not_block` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRefusesForeignLiveLease::test_same_worktree_restart_stays_idempotent` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestStealOverride::test_steal_succeeds_and_invalidates_the_other_worktrees_lease` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestDoubleDispatchIncidentRegression::test_incident_shape_end_to_end` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 0 error(s), 1196 warning(s), 209 waived
