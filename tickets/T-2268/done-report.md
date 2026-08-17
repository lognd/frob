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
