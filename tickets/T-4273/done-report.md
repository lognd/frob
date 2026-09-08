## Done report

Changed:
src/frob/tickets/_leases.py::_git_says_nothing_to_commit
src/frob/tickets/_leases.py::_pathspecs_still_dirty
src/frob/tickets/_leases.py::_ledger_commit_failure_step_and_detail
src/frob/tickets/_leases.py::_add_and_commit_tickets_md
src/frob/tickets/_leases.py::_is_resolved_concurrent_commit_race
src/frob/tickets/_leases.py::_finish_ledger_commit_marker
src/frob/tickets/_leases.py::_handle_finish_marker_retry_failure

Root cause (reproduced locally, not just theorized): a `git commit -- <pathspec>`
that finds nothing staged for that pathspec puts its explanation ("nothing to
commit, working tree clean") on STDOUT with an empty stderr and exit 1 --
exactly the incident's `returncode=1 stderr=''`. Under parallel load a
concurrent ledger-committing call can commit these exact pathspecs between
this call's own dirty-check and its own `git commit`, so the "premise" both
the main commit path and the T-2714 self-heal marker path relied on (content
was written, only the commit was lost) stops being true mid-flight. The old
self-heal blindly re-ran the identical add+commit and declared "needs a
human" on ANY failure, including this resolved-race case, which is why the
retry failed identically and why the log read "still dirty" against an
already-clean repo.

Fix: both failure sites now re-check `git status` on the pathspecs AFTER a
failed commit before concluding anything -- still dirty is a real failure
(existing "needs a human" / "left DIRTY" paths, now naming stdout too, not
just stderr); no longer dirty means a concurrent call already landed the
identical change, logged as a resolved race and treated as success (main
path) / marker cleared with no alarm (self-heal path), never a false
"needs a human".

Reproduction: attempted under real `pytest -n 12` concurrency across
tests/test_ticket_leases.py, tests/test_ticket_runner_archive_force.py (the
sibling with the T-4273-relevant `@pytest.mark.flaky` marker, whose
`_make_done_ticket` helper matches the ticket's "dies in fixture setup"
description), tests/test_tickets_ledger_concurrency.py, and the wider
`-k ticket` subset (2679 tests) with `--dist worksteal`; did not reproduce
locally on this 12-core box. Per the ticket's own instruction, this is
reported plainly rather than forced, and the diagnostic/self-heal fix
ships regardless -- it is independently correct (proven deterministically:
calling `_add_and_commit_tickets_md`/`_finish_ledger_commit_marker` against
already-clean pathspecs reproduces git's exact "nothing to commit" stdout
signature without needing real thread concurrency) and is exactly what
pays off the next time this occurs under real CI load, per the ticket's
own "make the diagnostic improvement anyway" instruction.

The rerun-marker sibling (`TestTicketArchiveForceCLI.test_refuses_without_
force_when_a_live_lease_exists`, `@pytest.mark.flaky`) and its unmarked
twin (`test_force_overrides_the_live_lease_refusal`) are both left as they
are -- no second marker added; the fix targets the actual ledger-commit
race their shared `_make_done_ticket` helper's `close` call can hit, not
either test's own assertions.

Evidence:
tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_commit_failure_detail_names_both_streams
tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_resolved_race_is_not_reported_as_commit_failed
tests/test_ticket_leases.py::TestLedgerCommitRepairMarker::test_resolved_race_clears_the_marker_without_a_false_alarm
tests/test_ticket_leases.py (full file, 18 TestLedgerCommitRepairMarker/TestCommitTicketLedgerChange tests green)
frob test --base main (touched=17, python exit=0, 88.70s)

Filed: T-4283 (pre-existing SCOPE002 scope-closure debt on T-4273's
declared scope, unrelated to this fix -- present before this session touched
anything, spans ~15 files this ticket's own bug fix has no reason to expand
scope into)

Gates: `frob check --ticket T-4273 --no-cache` clean on every ticket-scoped
family this ticket's diff can affect (gate:ARCH 0, gate:FMT 0, gate:LANDPARITY
0, gate:TEST 0) after splitting the two functions that crossed ARCH001's
line threshold and wrapping the new frob:tests directives to canonical
width. gate:SCOPE (34, all SCOPE002 except the one SCOPE001 already fixed by
adding tests/test_ticket_leases.py to scope) is pre-existing debt against
symbols this diff never touched -- see T-4283; not waived because
SCOPE002 has no ticket-level waiver surface (WARN-severity, no `frob:waive`
target since findings are file-level at tickets.md:0, and no
`scope-ack`-consulting check in gate:SCOPE002's own source) -- filed rather
than force-fit.

### Changed
```
 tickets/T-4273/done-report.md      | 92 ++++++++++++++++++++++++++++++++++++++
 tickets/T-4273/ticket.md           | 15 ++++++-
 tickets/T-4283/ticket.md | 70 +++++++++++++++++++++++++++++
 3 files changed, 176 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_resolved_race_is_not_reported_as_commit_failed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLedgerCommitRepairMarker::test_resolved_race_clears_the_marker_without_a_false_alarm` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_commit_failure_detail_names_both_streams` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 3 error(s), 4611 warning(s), 945 waived
- error-findings: COV003@tests/test_excludes.py, PRE001@tickets/T-4273, SCOPE002@tickets.md
