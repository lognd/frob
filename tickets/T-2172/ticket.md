---
id: T-2172
title: scripts/fleet_status.py::main crosses ARCH001/ARCH103 after T-2129/T-2133's
  land (230-line growth)
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- tests/unit/test_coordinator_scripts.py
- docs/guides/coordinator-scripts.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: tests + doc anchors for the ARCH001/ARCH103 main() split
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: tests + doc anchors for the ARCH001/ARCH103 main() split
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_coordinator_scripts.py::TestPrintTicketReadiness::test_prints_dispatchable_true
- tests/unit/test_coordinator_scripts.py::TestPrintTicketReadiness::test_prints_lease_scope_divergence_and_sibling_commits
- tests/unit/test_coordinator_scripts.py::TestPrintFleetReport::test_prints_all_four_sections
- tests/unit/test_coordinator_scripts.py::TestFleetStatusMain::test_ticket_readiness_prints_before_the_general_report
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2129/T-2133's land grew scripts/fleet_status.py by 230 lines, and its
`main()` crossed ARCH001 (78 lines, threshold 60) and ARCH103 (mixes I/O,
string-formatting, and 14 decision points in one body). These are
currently UNDISPOSED in the quarantine store and raising the verify
quarantine fleet-wide.

Fix: split `main()` into `_print_ticket_readiness(readiness) -> bool`
(the `TICKET <id>` block) and `_print_fleet_report(dirt, idle_seconds)
-> None` (the ROOT/QUARANTINE/LEASES/WORKTREES blocks), leaving `main`
itself as argument parsing plus the ordering/exit-code decision. Also
fixes the coordinator's own UX report: `--ticket T-####`'s readiness
block now prints FIRST, ahead of the general fleet report, instead of
being buried below it.

## Done report

Changed:
- scripts/fleet_status.py::main -- was 78 lines / 14 decision points
  (ARCH001/ARCH103); now argument parsing plus the ordering/exit-code
  decision only.
- scripts/fleet_status.py::_ticket_readiness_lines (new) -- pure-compute
  half of the old `TICKET <id>` print block (formatting + branching, no
  I/O).
- scripts/fleet_status.py::_print_ticket_readiness -- now I/O-only
  (loops over `_ticket_readiness_lines`'s output and prints it), so it
  no longer independently trips ARCH103's mixed-concern signal.
- scripts/fleet_status.py::_print_fleet_report (new) -- the ROOT/
  QUARANTINE/LEASES/WORKTREES print block, taking `dirt`/`idle_seconds`
  as arguments.
- scripts/fleet_status.py::main -- also fixes the coordinator's own UX
  report: `--ticket T-####`'s readiness block now prints FIRST, ahead of
  the general fleet report (previously buried below ROOT/QUARANTINE/
  LEASES/WORKTREES).
- docs/guides/coordinator-scripts.md -- new sections for
  `_ticket_readiness_lines`/`_print_ticket_readiness`/
  `_print_fleet_report`, updated `fleet_status-main` section.
- tests/unit/test_coordinator_scripts.py -- 4 new tests
  (TestPrintTicketReadiness x2, TestPrintFleetReport x1,
  TestFleetStatusMain.test_ticket_readiness_prints_before_the_general_report).

Evidence:
- tests/unit/test_coordinator_scripts.py::TestPrintTicketReadiness::test_prints_dispatchable_true
- tests/unit/test_coordinator_scripts.py::TestPrintTicketReadiness::test_prints_lease_scope_divergence_and_sibling_commits
- tests/unit/test_coordinator_scripts.py::TestPrintFleetReport::test_prints_all_four_sections
- tests/unit/test_coordinator_scripts.py::TestFleetStatusMain::test_ticket_readiness_prints_before_the_general_report
- `uv run pytest tests/unit/test_coordinator_scripts.py -o addopts="" -q`:
  48 passed (was 44 before this ticket's 4 new tests).
- Measured ARCH001/ARCH103 at the REAL path (`uv run frob check --only
  gates-native --only gates-fast --ticket T-2172 --json`,
  parsed with scripts/check_summary.py -- never a copied/extracted blob,
  per the coordinator's explicit caution): BEFORE this fix, `ARCH001:
  function main has 78 lines (threshold: 60)` and `ARCH103: main mixes
  I/O, string-formatting, and 14 decision points in one body`, both at
  scripts/fleet_status.py:356. Split once -- ARCH001 cleared but ARCH103
  re-fired on `_print_ticket_readiness` (4 decision points, still mixed
  I/O+formatting+branching). Split again (`_ticket_readiness_lines` vs
  `_print_ticket_readiness`) -- AFTER: zero ARCH findings anywhere in
  `scripts/fleet_status.py`, confirmed by grepping the same JSON report
  for `fleet_status` and finding no hits.
- `uv run frob check --land-parity`: 6 unscoped errors remain, ALL
  pre-existing and outside this ticket's own edits, newly visible only
  because `git merge main` picked up T-2155/T-2157's own just-landed
  code in the same pull: `ARCH001`/`DRIFT001` on
  `src/frob/app/ticket_runner/_land_cmd.py`, `ARCH103`/`COV001`/`TEST001`
  on `src/frob/tickets/_land_git_ops.py` (T-2155/T-2157's own new
  `reclaim_orphaned_squash_residue`), and the same pre-existing `TICK004`
  on T-0969 noted in T-2129/T-2133's own Done reports. None touch
  `scripts/fleet_status.py`, `tests/unit/test_coordinator_scripts.py`,
  or `docs/guides/coordinator-scripts.md`.

One process note worth recording: mid-ticket, `git diff main
--diff-filter=D` showed 6 files as deleted relative to `main`
(`tests/unit/test_land_lock_liveness.py`, two T-215x done-reports, two
T-217x ticket.md files). Investigated per the deletion-filter land rule
before proceeding -- NOT a real deletion: my worktree's own `main` ref
was current, but my branch itself had not been re-merged against it
since before T-2155/T-2157/T-2170/T-2171 landed. A second `git merge
main` picked up the missing files and the deletion-filter check went
clean (empty diff). No data was ever actually lost; this is recorded so
the pattern ("stale branch, current main ref" reads identically to a
real revert until you re-merge) doesn't need re-deriving.

Filed: none new.

Gates: `frob check --only gates-native --only gates-fast` clean of any
ARCH finding in `scripts/fleet_status.py`; `frob check --land-parity`'s
remaining 6 errors are pre-existing debt from T-2155/T-2157, confirmed
by file path (none in this ticket's scope).

### Changed
```
 docs/guides/coordinator-scripts.md     |  46 +++++++--
 scripts/fleet_status.py                | 182 ++++++++++++++++++++++-----------
 tests/unit/test_coordinator_scripts.py | 110 ++++++++++++++++++++
 tickets/T-2172/ticket.md     |  54 ++++++++++
 4 files changed, 324 insertions(+), 68 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestPrintTicketReadiness::test_prints_dispatchable_true` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintTicketReadiness::test_prints_lease_scope_divergence_and_sibling_commits` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintFleetReport::test_prints_all_four_sections` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestFleetStatusMain::test_ticket_readiness_prints_before_the_general_report` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_land_git_ops.py, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST001@src/frob/tickets/_land_git_ops.py, TICK004@tickets.md
