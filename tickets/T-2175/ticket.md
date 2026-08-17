---
id: T-2175
title: 'release-lease refuses a genuinely orphaned lease and its error message asserts
  ''a process holds it'' when zero processes do: the canned LeaseWorktreeMismatch
  text describes conditions it never checked'
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/worktree_runner.py
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_leases.py
  reason: repro + fix test for release-lease's holder-dead detection, CLI entry in
    worktree_runner.py
  actor: logan
  at: '2026-08-11'
evidence:
- tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_releases_a_scope_diverged_lease
- tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_releases_an_orphaned_lease
- tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_exits_1_for_a_live_worktree
designated_repro_test: tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_releases_a_scope_diverged_lease
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Done report

Changed:
- src/frob/app/worktree_runner.py::_lease_scope_diverged_from_ledger -- new helper: True iff a ticket's recorded lease scope is COMPLETELY disjoint from its current ledger scope, the id-reuse/renumber residue shape T-1806/T-2048's four staleness checks (path-gone/ticket-gone/ticket-terminal/holder-dead) do not cover
- src/frob/app/worktree_runner.py::_run_release_lease -- on LeaseWorktreeMismatch, checks the new scope-divergence signal and force-releases (via the existing force_release_lease primitive) when it fires; rewrites the refusal message to name only what was actually established instead of asserting three unverified conditions

Evidence:
- tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_releases_a_scope_diverged_lease (designated repro; FAILED_AT_PARENT confirmed at 42592fddf, the test-only commit, via --check-repro)
- tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_releases_an_orphaned_lease (pre-existing, still passes -- no regression)
- tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_exits_1_for_a_live_worktree (pre-existing, still passes -- the fix does not weaken this refusal, since a live ticket's lease scope always overlaps its own current ledger scope)

Full tests/test_ticket_leases.py: 132 passed, 0 failed (pytest -o addopts="").

Root cause confirmed against the actual live T-2114/T-2118 leases at investigation time: recorded_at ~04:18/04:28 UTC, checked ~08:46 UTC -- ~4.3h/4.5h old, both still INSIDE holder-dead's 6h TTL window, so the TTL gate genuinely could not have fired regardless of live-process state. The real signal was scope divergence: main's ledger shows T-2114 state=queued scope=['src/frob/app/ticket_runner/_land_cmd.py'], but the lease on disk recorded scope=['tests/test_ticket_land.py', 'src/frob/tickets/_leases.py'] -- zero overlap, confirming the id was reused/renumbered and the lease is residue from the OLD identity, not the current ticket.

Deliberately did NOT weaken lease_staleness_reason's existing holder-dead TTL gate (in src/frob/tickets/_leases.py, out of this ticket's scope) or add a bypass/--force flag -- a naive "drop TTL, trust a live-process snapshot alone" change was considered and rejected: it would have flipped test_release_lease_cli_exits_1_for_a_live_worktree's expected outcome, since that fixture also has no live process cwd'd into the worktree at scan time (matching the documented "no persistent process between tool calls" caveat in _leases.py's own docstring) -- confirming that signal alone is unsafe. Scope divergence is a narrower, positive, always-safe-for-live-tickets signal instead.

Filed: none. src/frob/tickets/_leases.py (where lease_staleness_reason itself lives) was independently confirmed BLOCKED for this ticket by T-2114's own live lease during this investigation (`frob ticket scope T-2175 --add src/frob/tickets/_leases.py` refused: ScopeLeaseConflict, held by in-progress T-2114) -- exactly the bootstrapping case the coordinator flagged. No _leases.py change was needed for this fix (the scope-divergence check is built entirely from that module's existing PUBLIC primitives: read_all_leases, force_release_lease), so this was not a blocker in the end, just confirmation that any future _leases.py-side fix for this class would have hit it.

Gates: frob check --only coverage --only archgate --ticket T-2175 shows zero findings against src/frob/app/worktree_runner.py (grep against fresh full output, confirmed empty).

### Changed
```
 src/frob/app/worktree_runner.py | 147 +++++++++++++++++++++++++++++++++-------
 tests/test_ticket_leases.py     |  54 +++++++++++++++
 tickets/T-2175/ticket.md        |  16 ++++-
 3 files changed, 192 insertions(+), 25 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_releases_a_scope_diverged_lease` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_releases_an_orphaned_lease` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_exits_1_for_a_live_worktree` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/graph/callgraph.py, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2175, SELFAUDIT001@design, TEST001@src/frob/graph/callgraph.py, TICK004@tickets.md
