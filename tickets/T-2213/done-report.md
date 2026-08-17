## Done report

Changed:
  scripts/fleet_status.py::ticket_readiness (split, ARCH001/COV001)
  scripts/fleet_status.py::_scope_diverges_from_lease (new, extracted)
  scripts/fleet_status.py::_ticket_dispatchable (new, extracted)
  docs/guides/coordinator-scripts.md (new anchors for the two extracted
    predicates; ticket_readiness entry updated to point at them)

Split along the questions ticket_readiness answers, per the ticket's own
explicit instruction NOT to split on line count: `lease`/`main`/
`worktrees_with_commits`/`open_blockers`/`scope_lease_collisions` were
already each answered by a separate existing function call
(ticket_lease/ticket_frontmatter_on_main/worktrees_touching_ticket/
_open_blocker_ids/scope_lease_collisions) -- the two things NOT already
delegated were two inline boolean expressions: the scope-divergence
check and the dispatchable verdict. Extracted those as
_scope_diverges_from_lease and _ticket_dispatchable, each a named
predicate with its own focused docstring (most of the huge original
docstring's per-field explanation moved into the predicate it now
belongs to). ticket_readiness itself stays the thin orchestrator that
gathers facts and hands them to the two predicates -- unaffected by the
next capability landing, since a new fact just adds one more line to the
orchestrator, not more inline boolean logic to re-trip ARCH001.

Restored the frob:doc edge to the REAL, already-existing anchor
(docs/guides/coordinator-scripts.md#ticket_readiness, confirmed present
before I touched anything) rather than adding a token anchor -- the
function had simply lost its `# frob:doc ...` directive comment somewhere
across the seven lands; the anchor point itself was never actually
missing.

Evidence: tests/system/test_fleet_status_ticket_readiness_arch001.py::TestFleetStatusTicketReadinessArch001::test_ticket_readiness_is_not_an_arch001_finding
  (new repro test: runs the real `frob check --only arch` CLI and asserts
  "ticket_readiness" no longer appears in any ARCH001/ARCH103 finding.
  FAILED_AT_PARENT confirmed at 35b919de2 (repro-only commit); PASSED
  after the fix commit 67d7a03cc.)
  Also bound to acceptance[0] (measured baseline), acceptance[1] (split
  shape + doc-edge restoration).
  Direct pytest run (frob test's own strata sub-suite failed on unrelated,
  pre-existing repo-wide self-conformance GAP findings -- nothing under
  scripts/ or docs/guides/coordinator-scripts.md, confirmed by inspection):
  tests/unit/test_coordinator_scripts.py + the new repro test -- 95
  collected, 0 failed.
  `frob check --only arch` confirms zero ARCH001/ARCH103 findings naming
  ticket_readiness (only a pre-existing, unrelated LARGE001-class
  whole-file finding for fleet_status.py's 1740-line total, not scoped to
  this ticket).

Filed: none

Gates: frob check --ticket T-2213 -- gate:SCOPE/gate:PREWORK clean after
  a scope refresh (scoped the new test file and the touched doc); no
  gate:AFFECT or gate:FMT findings on this diff; gate:RENDER's 7 findings
  are in src/frob/release/_cli.py and src/frob/scaffold/_skills_sync.py,
  unrelated files, pre-existing repo-wide per the check's own scope-note.

### Changed
```
 docs/guides/coordinator-scripts.md                 |  36 ++++--
 scripts/fleet_status.py                            | 143 ++++++++++++---------
 .../test_fleet_status_ticket_readiness_arch001.py  |  25 ++++
 tickets/T-2213/ticket.md                           |  29 ++++-
 4 files changed, 161 insertions(+), 72 deletions(-)
```

### Evidence
- `tests/system/test_fleet_status_ticket_readiness_arch001.py::TestFleetStatusTicketReadinessArch001::test_ticket_readiness_is_not_an_arch001_finding` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/scaffold/_skills_sync.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1335, COV003@tickets/T-1353, COV003@tickets/T-1362, COV003@tickets/T-1363, COV003@tickets/T-1373, COV003@tickets/T-1397, COV003@tickets/T-1426, COV003@tickets/T-1433, COV003@tickets/T-1526, COV005@scripts/fleet_status.py, DOC001@docs/commands/release.md, DOC002@src/frob/scaffold/_skills_sync.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2213/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2213/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2213/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, RENDER001@src/frob/release/_cli.py, RENDER001@src/frob/scaffold/_skills_sync.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
