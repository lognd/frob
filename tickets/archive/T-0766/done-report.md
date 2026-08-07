## Done report

Added `resolve_lease(root, ticket_id, invoking_worktree)` to
`src/frob/tickets/_leases.py`: the pinned, per-ticket lease-resolution
primitive the ticket's acceptance criterion asks for. It reads exactly one
ticket's own lease file directly by its known path (new private
`_read_one_lease`, bypassing `read_all_leases`'s glob/iteration entirely --
so there is no iteration order, mtime, or "first match" for a cross-talk
bug to hide in), then validates the recorded worktree against the invoking
worktree. `Err(NoLeaseForTicket)` if the ticket has no lease at all;
`Err(LeaseWorktreeMismatch)` if it has a lease but for a DIFFERENT
worktree -- both name `frob ticket start <id>` as the remedy, matching the
T-0695 incident's own observed fix. Added both new `LeaseError` members.

Root cause: investigated `frob check --ticket`'s actual resolution path
(`active_ticket`/`_resolve_ticket` in gates/__init__.py, check_runner.py)
and confirmed it currently performs NO cross-worktree lease consultation
at all -- ticket id comes purely from `--ticket`/branch name, and
`enforce_worktree_lease` (the FROB_WORKTREE guard) is wired into
ack/coverage/baseline but not into check_runner.py. I could not reproduce
the exact T-0695 cross-talk mechanism inside the current check code path
in the time available; the module previously had NO ticket-pinned,
fail-loud lease resolution primitive at all (only `read_all_leases`, a
scan-everything read with no per-ticket ownership check), which is the
structural gap the ticket's acceptance criterion describes and this
closes. Filed T-0787 to wire `resolve_lease` (and/or
`enforce_worktree_lease`) into check_runner.py's actual entry point as a
follow-up, since that requires touching files outside this ticket's
declared scope. (Originally filed as a worktree draft that was lost when
the worktree was removed before its land finalized -- coordinator
refiled it verbatim as T-0787.)

Deviation: uv.lock and pyproject.toml's version line churn during every
`uv run`/`frob check` invocation in this worktree (pre-existing artifact,
see commit d27fbcec) and were reverted before every commit; not part of
this ticket's diff. `git diff main --diff-filter=D` shows two test files
(tests/system/test_spawn_budget.py, tests/test_perf_loop_invariant_effect_lock.py)
because main has advanced past this worktree's merge point since warm-up
(added there, not deleted here) -- confirmed via `git show main:<path>`
existing and not present at this worktree's merge base; not a revert of
this worktree's own work.

### Changed
(no changed files detected)

### Evidence
- `tests/test_tickets_leases.py::TestResolveLease::test_resolves_own_ticket_own_worktree` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestResolveLease::test_never_returns_a_sibling_tickets_lease` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestResolveLease::test_no_lease_for_ticket_fails_loudly` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestResolveLease::test_lease_recorded_for_a_different_worktree_fails_loudly` (pytest node id, verified passing when recorded)
