## Done report

test_ticket_show_reads_worktrees_own_ledger asserted the resolved
worktree path appears in `frob ticket show`'s default-verbosity output.
That assertion was introduced 2026-07-18 (534d91c2), when the ticket
CLI's default output still carried the full frob.gitio spawn-log
firehose (including the resolved -C path) alongside the runner's own
formatted line.

T-0768 (2026-07-22, "quiet diagnostic logger noise in frob ticket CLI
by default") deliberately clamped the `frob` logger tree to WARNING at
default verbosity, leaving only the ticket runner's own INFO line
visible -- a genuine, intentional feature, not a bug. That silently
broke this test's path-presence assertions: `frob ticket show` at
default verbosity now prints only the ticket line
("T-draft-... [queued] wt-only (bug)\nblocked_by=... scope=...\n"),
which never contains any filesystem path. Verified with a scratch
worktree: default-verbosity `show` output has 0 occurrences of the
worktree path; `frob ticket -v show` (restoring the gitio firehose)
has 4.

git log across the last ~30h of lands touching
src/frob/app/ticket_runner.py, src/frob/tickets/__init__.py, and
src/frob/tickets/_leases.py shows no changes to _show/display_state/
new_ticket's lease-recording path in that window -- T-0768 (5 days
before this investigation) is the actual, sole root cause; this test
had simply been silently red since then and was not caught by an
intervening coverage stamp.

Fix: pass `-v` (`frob ticket -v show <id>`) so the diagnostic firehose
that carries the resolved root path is restored for this one
assertion, preserving the test's original intent exactly instead of
weakening it -- `"wt-only" in out` alone would already prove the
worktree's ledger (not main's) was read, since the ticket only exists
there, but the path assertions add a stronger, more direct check that
this fix keeps meaningful rather than deleting. No production code
touched; T-0768's deliberate default-quiet behavior is left intact.

### Changed
(no changed files detected)

### Evidence
- `tests/system/test_cli_ticket_worktree_root.py::TestTicketRootFromLinkedWorktree::test_ticket_show_reads_worktrees_own_ledger` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 12 error(s), 1777 warning(s), 358 waived
- error-findings: COV001@src/frob/arch/_models.py, COV001@src/frob/gitlog/__init__.py, COV001@src/frob/process/parsers/common.py, COV001@src/frob/render/_color.py, COV001@src/frob/render/_elements.py, DEPR005@tests/system/test_cli_ticket_worktree_root.py, DEPR005@tests/test_gates.py, DEPR005@tests/test_ticket_land.py, DEPR005@tests/test_vet.py, INV006@src/frob/gates/_deprecated_baseline.py, PERF003@src/frob/arch/_cpp_mayraise.py, PERF004@src/frob/arch/_cpp_mayraise.py
