## Done report

Changed:
- scripts/fleet_status.py::ticket_lease (new) -- reads
  `.git/frob-leases/<id>.json` directly for one ticket id.
- scripts/fleet_status.py::ticket_frontmatter_on_main (new) -- hand-parses
  `state:`/`scope:` from `main:tickets/<id>/ticket.md`'s YAML frontmatter
  via `git show` (no `import yaml`, staying plain-stdlib per the module's
  existing contract).
- scripts/fleet_status.py::worktrees_touching_ticket (new) -- per live
  worktree, `git log main..HEAD -- tickets/<id>/` to detect unlanded
  commits for a given ticket on a sibling branch.
- scripts/fleet_status.py::ticket_readiness (new) -- combines the three
  above into `{lease, main, scope_diverges, worktrees_with_commits,
  dispatchable}`; `scope_diverges` is True when a live lease's scope
  differs from main's declared scope (the requested "single highest-value
  signal"); `dispatchable` is False whenever a lease is held, another
  worktree already has commits for the ticket, or main's state is
  done/dropped/in-progress.
- scripts/fleet_status.py::main -- new `--ticket T-####` flag: prints the
  readiness report and folds `not dispatchable` into the exit code
  alongside root dirt.
- docs/guides/coordinator-scripts.md -- new sections for the four
  functions above plus an updated `fleet_status-main` section/usage line.
- tests/unit/test_coordinator_scripts.py -- 13 new tests (TestTicketLease,
  TestTicketFrontmatterOnMain, TestWorktreesTouchingTicket,
  TestTicketReadiness, plus two on TestFleetStatusMain for `--ticket`).

Did NOT shell out to `frob ticket show` (reads git/`.git/frob-leases`
directly, per the ticket's explicit constraint) and did NOT infer
liveness from worktree commit age (uses the lease's own `recorded_at`
and a direct `main..HEAD` commit check instead, per the ticket's explicit
constraint). Reused `fleet_status.py`'s own `_git`/`LEASES`/`WORKTREES`
rather than duplicating them, and extended `fleet_status.py` itself
(not a sibling script) since the ticket's own declared scope was
`scripts/fleet_status.py` only -- a new sibling file would not have
matched that glob.

Evidence:
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_dispatchable_when_no_lease_no_commits_no_divergence
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_a_live_lease_exists
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_another_branch_already_has_commits
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_flags_scope_divergence_between_the_live_lease_and_main
- tests/unit/test_coordinator_scripts.py::TestFleetStatusMain::test_ticket_flag_exits_one_when_not_dispatchable
- tests/unit/test_coordinator_scripts.py::TestFleetStatusMain::test_ticket_flag_exits_zero_when_dispatchable
- tests/unit/test_coordinator_scripts.py::TestTicketLease::test_reads_a_live_lease
- tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain::test_reads_state_and_scope
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_finds_a_branch_with_unlanded_commits
All 13 new tests committed alone first and confirmed FAILING
(`AttributeError: ... has no attribute 'ticket_readiness'` etc, 13 failed/
31 passed) against the pre-fix tree, then PASSING (44 passed) once
scripts/fleet_status.py + docs were committed separately.
- `uv run pytest tests/unit/test_coordinator_scripts.py -o addopts="" -q`:
  44 passed (was 31 before this ticket's 13 new tests).
- `uv run frob check --land-parity`: clean -- 0 unscoped errors.
- `uv run frob check --only scope --only tickets --ticket T-2133`: 4
  errors remain, all pre-existing and none introduced by this ticket's
  own edits -- 3 SCOPE001 findings on `tickets/T-2129/*` and
  `tickets/T-2167/*` (T-2129's own still-unlanded ledger
  writes, sharing this series worktree; these clear once T-2129 lands)
  and 1 TICK004 on T-0969 (an unrelated pre-existing rotting-ticket
  finding, confirmed present in tickets.md independent of this ticket).

Filed: none new (T-2167 was already filed under T-2129).

Gates: `frob check --land-parity` clean; `frob check --only scope --only
tickets --ticket T-2133` shows only the two pre-existing findings
explained above (no waiver needed -- neither is this ticket's own scope
or a new finding).

### Changed
```
 docs/guides/coordinator-scripts.md        |  71 ++++++++-
 scripts/fleet_status.py                   | 228 +++++++++++++++++++++++++++-
 src/frob/app/ticket_runner/_land_cmd.py   | 111 +++++++++-----
 tests/test_ticket_work_and_land_finish.py |  39 +++++
 tests/unit/test_coordinator_scripts.py    | 242 ++++++++++++++++++++++++++++++
 tickets/T-2129/done-report.md             |  76 ++++++++++
 tickets/T-2129/ticket.md                  |  38 ++++-
 tickets/T-2133/ticket.md                  |  27 +++-
 tickets/T-2167/ticket.md        |  63 ++++++++
 9 files changed, 848 insertions(+), 47 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_dispatchable_when_no_lease_no_commits_no_divergence` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_a_live_lease_exists` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_another_branch_already_has_commits` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_flags_scope_divergence_between_the_live_lease_and_main` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestFleetStatusMain::test_ticket_flag_exits_one_when_not_dispatchable` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestFleetStatusMain::test_ticket_flag_exits_zero_when_dispatchable` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestTicketLease::test_reads_a_live_lease` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain::test_reads_state_and_scope` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_finds_a_branch_with_unlanded_commits` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@scripts/fleet_status.py, ARCH103@scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2129/scripts/fleet_status.py, PRE001@tickets/T-2133, SELFAUDIT001@design, TICK004@tickets.md
