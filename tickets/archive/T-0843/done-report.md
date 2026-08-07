## Done report

Changed:
- src/frob/tickets/__init__.py: `archive()` -- moved the T-0764 live-lease
  guard from "any live lease anywhere in the repo" to "a live lease on a
  ticket this call would actually move into tickets-archive.md"
  (intersect `live_leases` against `to_archive`, computed after acquiring
  `ledger_lock`); log message now says "run in a quiet window or pass
  --force" instead of "force=True".
- src/frob/tickets/_models.py: `TicketError.ArchiveLiveLeaseExists` --
  hint text now says "run in a quiet window or pass --force to override"
  (was "pass force=True to override", the internal python kwarg, not the
  CLI surface).
- tests/test_tickets.py: `TestArchiveRefusesDuringInFlightWork` -- kept
  `test_archive_refuses_when_a_live_lease_exists`'s name (T-0764's
  evidence cites it) but repointed its live lease onto the archived
  ticket itself; same for `test_archive_force_overrides_the_live_lease_refusal`
  and `test_archive_ignores_a_stale_lease_from_a_removed_worktree`; added
  `test_archive_ignores_a_live_lease_for_a_ticket_it_would_not_touch` for
  the new narrowed-guard behavior.
- tests/test_ticket_runner_archive_force.py: CLI-level tests repointed
  their live lease onto the ticket being archived (T-0001) instead of an
  unrelated ticket (T-0002), so they still exercise the (now narrower)
  refusal path end to end.

Filed: none. The two touched-but-originally-unlisted files
(src/frob/tickets/_models.py, tests/test_tickets.py) were added to
T-0843's own scope via `frob ticket scope --add --reason-file` (see
scope_changes above) rather than filed separately, since the exact
"force=True" hint string and this guard's own regression tests live
there -- not out-of-scope work, just mis-scoped at ticket-filing time.

Evidence:
tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_refuses_when_a_live_lease_exists
tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_force_overrides_the_live_lease_refusal
tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_ignores_a_stale_lease_from_a_removed_worktree
tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_ignores_a_live_lease_for_a_ticket_it_would_not_touch
tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists
tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal
tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_with_no_live_leases_stays_quiet
(7/7 passed: `uv run pytest tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork tests/test_ticket_runner_archive_force.py -p no:cacheprovider -q` -> "......." 7 passed)

Gates: `frob check --ticket T-0843` clean across all five stage groups
(chunked `--only` loop per T-0574/T-0627 discipline) -- lint 0/0,
static 0 errors (pre-existing exports/dup/arch warnings only),
gates-fast 0 errors (after fixing the COV002/COV003/SCOPE001/PRE001
findings the scope-add and rename produced), gates-native 0 errors,
gates-security 0 errors. `git diff main --diff-filter=D --stat` empty
(no unintended deletions).

Known tooling issue hit and worked around: `frob ticket done-report
--why-file` hung indefinitely for this ticket (bug T-0887, per
coordinator) -- killed the hung process and wrote this Done report
block directly into tickets.md instead.
