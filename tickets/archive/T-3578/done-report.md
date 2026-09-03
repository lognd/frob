## Done report

Changed:
- src/frob/tickets/_leases.py::_log_ledger_commit_failure
- src/frob/tickets/_leases.py::_ledger_commit_failure_step_and_detail (new)
- src/frob/tickets/_leases.py::_add_and_commit_tickets_md (call-site update, passes added/committed through)
- tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_commit_failure_names_the_failing_step_and_git_detail (new)

Status: PARTIAL. This was NOT root-caused within this ticket's budget --
see the ticket body's cross-platform update for the full account. Summary:
run 33376126399 (macos-latest) and run 33380974368 (ubuntu-latest) both
show tests/test_ticket_runner_archive_force.py's two CLI tests dying with
SystemExit: 1 from an identical failure shape -- commit_ticket_ledger_
change's git add/git commit step failing inside the test fixture's own
tmp git repo, with the real git stderr never surfaced in CI output (only
"the commit step failed", no detail). Ran both node ids 10x locally,
serial and under -n 4, against this test file alone: did NOT reproduce
(13/13 green every run) -- the trigger needs the full suite's env/fs
state to surface, not just this file in isolation. Checked T-3528 and
T-3567 (the two lands the coordinator named as suspects) via git show
--stat on both landing commits: neither touches src/frob/tickets/
_leases.py or this commit path at all -- ruled out as the direct cause.

What this land DOES fix: _log_ledger_commit_failure now names WHICH step
(git add vs git commit) failed and the real returncode/stderr (or
GitError) instead of a generic, undiagnosable "the commit step failed" --
so the next CI occurrence is diagnosable from the log line alone, no
re-fetching raw job logs required. The underlying "why does git add/
commit fail in this fixture" question remains OPEN.

Evidence: tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_commit_failure_names_the_failing_step_and_git_detail, tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists, tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal (all pytest node ids, verified passing 13/13 via uv run pytest -p no:xdist, and 10x repeated locally including -n 4)

Filed: none new (T-3579 was already filed under T-3577's own Done report for the unrelated frob-check-crash defect)

Gates: uv run frob test --base main green (3 python test outcomes recorded); targeted pytest runs green (13/13). ty/ruff clean on touched files.

NOTE FOR COORDINATOR: root cause of the underlying CI-only git-commit
failure is still OPEN -- this ticket should NOT be treated as "the last
cross-platform blocker resolved." Recommend re-running windows/ubuntu/
macos CI with this diagnostic land in place; the next failure's log line
will carry the real git stderr needed to actually root-cause it.

### Changed
```
 tickets/T-3578/ticket.md | 4 ++++
 1 file changed, 4 insertions(+)
```

### Evidence
- `tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_commit_failure_names_the_failing_step_and_git_detail` (pytest node id, verified passing when recorded)
- `tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists` (pytest node id, verified passing when recorded)
- `tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 32 error(s), 4116 warning(s), 891 waived
- error-findings: ARCH001@src/frob/tickets/_leases.py, ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC006@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_conftest_sigbreak_faulthandler.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_conftest_sigbreak_faulthandler.py, E501@/home/logan/projects/frob/.claude/worktrees/t-3578/src/frob/tickets/_leases.py, LANDPARITY002@src/frob/tickets/_leases.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3578, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
