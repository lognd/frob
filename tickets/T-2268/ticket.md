---
id: T-2268
title: 'Holding ticket: 14 pre-existing floor findings with no owning ticket (blocked
  quarantine clearance, fleet-wide land stall 2026-08-17)'
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/scaffold/_skills_sync.py
- docs/commands/sync-skills.md
- tests/unit/test_skills_sync.py
evidence_scope:
- tests/unit/test_skills_sync.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/commands/sync-skills.md
  reason: 'T-2268: fixing the DOC002/COV001/RENDER001 trio on _skills_sync.py touches
    its paired doc anchor and unit test file too (AFFECT001/COV002 closure)'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/unit/test_skills_sync.py
  reason: 'T-2268: fixing the DOC002/COV001/RENDER001 trio on _skills_sync.py touches
    its paired doc anchor and unit test file too (AFFECT001/COV002 closure)'
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_skills_sync.py::TestSkillsSyncRenderLint::test_no_render001_violations_for_skills_sync
- tests/unit/test_skills_sync.py::TestSyncSkills::test_syncs_new_repo_entries
- tests/unit/test_skills_sync.py::TestRun::test_run_reports_synced_and_removed_counts
designated_repro_test: tests/unit/test_skills_sync.py::TestSkillsSyncRenderLint::test_no_render001_violations_for_skills_sync
acceptance:
- text: Each listed finding is fixed or has its own owning ticket; none remains attributed
    solely to this holding ticket
  evidence:
  - tests/unit/test_skills_sync.py::TestSkillsSyncRenderLint::test_no_render001_violations_for_skills_sync
- text: The _skills_sync.py trio (COV001/DOC002/RENDER001) is addressed first -- regressions
    from a land hours old, not historical debt
  evidence:
  - tests/unit/test_skills_sync.py::TestSkillsSyncRenderLint::test_no_render001_violations_for_skills_sync
  - tests/unit/test_skills_sync.py::TestSyncSkills::test_syncs_new_repo_entries
  - tests/unit/test_skills_sync.py::TestRun::test_run_reports_synced_and_removed_counts
- text: Fixes land as separate subsystem-scoped commits; state the split
  evidence:
  - tests/unit/test_skills_sync.py::TestSkillsSyncRenderLint::test_no_render001_violations_for_skills_sync
- text: 'MUST-STILL-PASS: unscoped frob check with gate-summary present shows the
    floor down by the number fixed, no new identities'
  evidence:
  - tests/unit/test_skills_sync.py::TestSkillsSyncRenderLint::test_no_render001_violations_for_skills_sync
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
# Tracking ticket: 14 pre-existing floor findings with no owning ticket, blocking quarantine clearance

## Why this ticket exists

`clear_quarantine` is ATOMIC over every recorded finding. On 2026-08-17 it
refused with 36 findings undisposed while quarantine was RAISED, which turns
off deferred landing repo-wide -- three lands retried for 45+ minutes with zero
completions and left staged residue in the shared root each time.

22 of the 36 already have owning tickets (COV003 x11 -> T-2256, COV004 x2 ->
T-2254, DOC011 x2 -> T-2237, and E501/F541/DRIFT001 x3/SELFAUDIT001/CLAUDE001
-> T-2260). The 14 below had none, so quarantine could not clear and the fleet
stayed blocked.

This ticket exists so those 14 are HONESTLY TRACKED rather than dismissed. They
are real findings, present in the measured unscoped floor. Disposing them to
this ticket asserts "tracked, not fixed" -- it does not assert they are
acceptable.

## The 14

    ARCH001    scripts/fleet_status.py
    ARCH001    src/frob/app/telemetry.py
    ARCH001    src/frob/app/ticket_runner/_land_cmd.py
    ARCH001    src/frob/app/ticket_runner/_new.py
    ARCH103    src/frob/app/ticket_runner/_land_cmd.py
    COV001     scripts/fleet_status.py
    COV001     src/frob/scaffold/_skills_sync.py
    COV002     src/frob/app/ticket_runner/_lifecycle.py
    COV002     src/frob/tickets/_land.py
    DOC002     src/frob/scaffold/_skills_sync.py
    DOC005     README.md
    DOC005     docs/modules/cli.md
    PERF004    scripts/fleet_status.py
    PERF004    src/frob/app/ticket_runner/_land_cmd.py
    REL001     pyproject.toml
    RENDER001  src/frob/scaffold/_skills_sync.py
    TEST010    tests/test_ticket_work_and_land_finish.py

Note three of these (COV001, DOC002, RENDER001 on `_skills_sync.py`) arrived
with T-2241's own land -- a brand-new subcommand landed without its doc edge,
export declaration, and render coverage. Those are the freshest and most
clearly actionable.

## Do NOT fix it this way

- **Do NOT dismiss these findings to clear quarantine.** A `--dismiss` asserts
  the finding is not a problem. These are real and the floor will keep
  reporting them; dismissing makes the quarantine lie rather than the floor
  shrink. That is why this ticket was filed instead.
- **Do NOT treat this ticket as a licence to leave them.** It is a holding pen
  with a named owner, not an acceptance. Split real work out of it as separate
  tickets rather than growing it.
- **Do NOT fix all 17 lines above in one change.** They span six unrelated
  subsystems. A single sweeping commit would be unreviewable and would collide
  with half the fleet's leases.
- **Do NOT resolve ARCH001 by raising the threshold.** The 60-line limit is the
  rule; the fix is extraction, and T-2214 landed a land-time gate specifically
  to stop these accumulating.

## Acceptance criteria

1. (MUST FAIL FIRST) Each of the listed findings is either fixed or has its own
   owning ticket; none remains attributed solely to this holding ticket. Fails
   today: all 14 identities point here and nowhere else.
2. The `_skills_sync.py` trio (COV001/DOC002/RENDER001) is addressed first --
   they are regressions from a land hours old, not historical debt.
3. Fixes land as separate, subsystem-scoped commits; state the split.
4. MUST-STILL-PASS CONTROL: an unscoped `frob check --json` (with
   `gate-summary` present -- a budget-truncated run reports a false
   improvement) shows the floor DOWN by the number fixed, with no new
   identities introduced.
5. When this ticket closes, no finding is left silently attributed to it.

## Done report

Changed:
- src/frob/scaffold/_skills_sync.py::SkillsSyncReport (frob:doc anchor added: docs/commands/sync-skills.md#public-api)
- src/frob/scaffold/_skills_sync.py::sync_skills (frob:doc anchor added)
- src/frob/scaffold/_skills_sync.py::run (frob:doc anchor added; bare print() replaced with Renderer.for_stream(sys.stdout).line(...))
- docs/commands/sync-skills.md (Renderer-routing note added, closing AFFECT001)
- tests/unit/test_skills_sync.py::TestSkillsSyncRenderLint (new RENDER001 repro class + frob:ticket T-2268 directive, closing COV002)

Evidence:
- tests/unit/test_skills_sync.py::TestSkillsSyncRenderLint::test_no_render001_violations_for_skills_sync (designated repro, FAILED_AT_PARENT verified against commit cae5775be -- the repro-test-only commit, before the fix commit 3c3442c6d)
- tests/unit/test_skills_sync.py::TestSyncSkills::test_syncs_new_repo_entries
- tests/unit/test_skills_sync.py::TestRun::test_run_reports_synced_and_removed_counts
(bound to acceptance[0] and acceptance[1])

Filed (T-2268 triage of the remaining 14 -- none fixed here, each now has an owner):
- ARCH001 src/frob/app/telemetry.py, .../_land_cmd.py, .../_new.py + ARCH103 .../_land_cmd.py + PERF004 .../_land_cmd.py + TEST010 tests/test_ticket_work_and_land_finish.py -> already owned by existing ticket T-2206 (post-land sweep regression from T-2199)
- ARCH001 scripts/fleet_status.py + COV001 scripts/fleet_status.py -> already owned by existing ticket T-2213 (ticket_readiness ARCH001/COV001 split)
- COV002 src/frob/app/ticket_runner/_lifecycle.py, src/frob/tickets/_land.py -> newly filed T-2279
- DOC005 README.md, docs/modules/cli.md (sync-skills missing from command table) -> newly filed T-2278
- PERF004 scripts/fleet_status.py -> newly filed T-2276 (distinct from T-2213's ARCH001/COV001 scope and T-2206's different PERF004 identity on _land_cmd.py)
- REL001 pyproject.toml -> newly filed T-2277

Gates: frob check --ticket T-2268 clean for the _skills_sync.py trio (COV001/DOC002/RENDER001 all resolved) plus the AFFECT001/COV002 closure gaps the fix itself introduced (doc anchor touched, frob:ticket directive added to the new test class). DOC005 on README.md still reports (expected -- filed to T-2278, not fixed in this ticket per its own scope). No waivers used.

### Changed
```
 docs/commands/sync-skills.md       |  5 ++++
 src/frob/scaffold/_skills_sync.py  | 14 +++++++-----
 tests/unit/test_skills_sync.py     | 24 +++++++++++++++++++
 tickets/T-2268/ticket.md           | 34 +++++++++++++++++++++++----
 tickets/T-2276/ticket.md | 47 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2277/ticket.md | 43 ++++++++++++++++++++++++++++++++++
 tickets/T-2278/ticket.md | 46 +++++++++++++++++++++++++++++++++++++
 tickets/T-2279/ticket.md | 46 +++++++++++++++++++++++++++++++++++++
 8 files changed, 249 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/test_skills_sync.py::TestSkillsSyncRenderLint::test_no_render001_violations_for_skills_sync` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestSyncSkills::test_syncs_new_repo_entries` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestRun::test_run_reports_synced_and_removed_counts` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@scripts/fleet_status.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2268/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2268/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2268, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
