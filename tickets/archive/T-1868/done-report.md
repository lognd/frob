## Done report

Root cause confirmed (not assumed) by direct reproduction: `_scope_add_
conflicts` only checked the requesting worktree's own LOCAL ticket-ledger
read (`_load_ticket_and_queue`), which lags a sibling worktree's `start`
until this worktree merges main. `frob ticket start`'s own foreign-lease
refusal instead reads `read_all_leases`, the cross-worktree lease
side-channel under the shared git-common-dir, which is live the instant
a sibling worktree records or updates its lease -- no merge needed.
`scope --add` used only the merge-dependent source, so two in-progress
tickets in different, unconverged worktrees could hold the identical
path (T-1863/T-1822 both held design/frob.strata 36s apart, neither
refused; independently reproduced again during T-1648's own land against
me).

Fix: `_scope_add_conflicts` (frob.tickets._scope) now also checks every
other ticket's LIVE lease via a new `_scope_add_live_lease_conflict`
helper, in addition to (never instead of) the existing queue-based
check. TTL-expired leases excluded (mirrors `_refuse_if_foreign_live_
lease`); T-1356's same-worktree exemption and T-0561's new-file carve-out
both apply identically. The pre-existing queue-based loop was split into
its own `_scope_add_queue_conflict` helper (ARCH001: the combined
function exceeded the 60-line threshold once the live-lease half was
added).

Regression test (not merely a unit test of the check function, per the
ticket's own explicit requirement): tests/test_ticket_leases_cross_
worktree.py::TestScopeAddRefusesLiveCrossWorktreeLease uses TWO real,
separate `git worktree` checkouts of one repository (the existing T-0473
fixture pattern), ticket A starting in the first and ticket B
independently in the second (no merge between them anywhere in the
test), and asserts `scope --add` for ticket A's leased path from the
second worktree is refused. Verified by reverting the fix in place and
confirming this exact test fails (AssertionError on the refusal
assertion) before re-applying it.

Requirement 2 (audit other scope-mutating paths for the same gap):
surveyed every `write_ticket`/`ticket.scope` write site in
src/frob/tickets/ and src/frob/app/ticket_runner/. No other path writes
ticket.scope outside mutate_scope itself.
frob.tickets._land_squash._v2_effective_scope widens a scope by
appending tickets/<id>/*, but only on an in-memory copy for one land's
own conflict-resolution decision -- never persisted, and the appended
glob is always the ticket's own id-shard (cannot collide with any other
ticket by construction). _auto_resolve_out_of_scope_conflicts (land's
merge-conflict auto-resolver) reads ticket.scope to pick a resolution
strategy but never widens or writes it. No other gap of this shape
found.

Requirement 3 (deciding what to do about the sys sync-interface ->
COV002/SELFAUDIT -> scope-add pressure that generated the T-1648
incident) is EXPLICITLY OUT OF SCOPE for this ticket by owner directive:
frob sys sync-interface is being deleted outright (T-1870 -- a grep
across every src/frob/strata/ and src/frob/gates/ reader of `.interface`
found zero consumers, confirming the auto-sync loop was closed and
unenforcing). T-1868 fixes the mutual-exclusion bug that pressure
exposed; T-1870 removes the pressure itself. Not silently dropped --
explicitly delegated.

Documentation: a docs/modules/tickets.md section for this fix was
drafted but NOT landed here -- the file was leased by in-progress T-1873
at land time (itself a live demonstration of this ticket's own fix
correctly refusing a scope-add into a currently-held path: my own
attempt to scope-add docs/modules/tickets.md into T-1868 was refused by
the new check, naming T-1873 as holder). Filed T-1878 to add
the section once that lease frees, and left an in-code frob:todo
pointing at it on _scope_add_live_lease_conflict.

Filed: T-1878 (deferred docs/modules/tickets.md section).

### Changed
```
 tickets/T-1868/ticket.md           | 39 +++++++++++++++++++++++++++++++++++++-
 tickets/T-1878/ticket.md | 32 +++++++++++++++++++++++++++++++
 2 files changed, 70 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 828 warning(s), 742 waived
- error-findings: none (measured, zero errors)
