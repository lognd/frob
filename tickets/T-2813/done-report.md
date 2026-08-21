## Done report

Batch 13 of the T-2359 ruff-format-only reformat epic. 13 files
re-measured against current main (b22f3adb6) via `ruff format --check .`
(45 files remaining before this batch). Format-only, no semantic changes.

File-selection note: picked from the 45 remaining files. Fresh leases
re-pulled per playbook, not reused from any prior snapshot:
scripts/fleet_status.py showed 2 lands in flight (T-2755, T-2805) plus 7
live leases (T-1686 root-resident, T-2359, T-2369, T-2370, T-2373,
T-2755, T-2805, T-2806). Read each live entry's .git/frob-leases/*.json
scope directly: T-2369/T-2370/T-2373 all read scope: [] (epic-rollup
shape). T-2369's live worktree has genuine dirty files under
src/frob/gates/ and src/frob/perf/ -- none overlap this batch's
candidate pool. T-2370's and T-2373's worktrees showed a clean git
status with only already-landed batch-11/12 content in their branch
history (T-2808/T-2811), not live edits -- but per the coordinator's
explicit warning about T-2373's empty-lease/live-claim mismatch,
excluded its historically-claimed files anyway as a precaution:
tests/test_ticket_land.py, tests/test_ticket_work_and_land_finish.py,
tests/test_tickets_organization.py, tests/test_tickets_priority.py,
tests/unit/test_app_runners_batch6.py,
tests/unit/test_app_runners_t2395_contention.py. Also excluded T-2806's
declared live scope (src/frob/gates/__init__.py,
tests/unit/test_check.py) and T-2805's/T-2755's declared scopes (no
overlap with the candidate pool anyway). frob ticket new/start accepted
this batch's scope with zero lease collisions.

Diff reviewed by hand across all 13 files: pure ruff-format whitespace/
line-wrap changes (20 insertions, 41 deletions total across the batch),
no logic changes. frob format needed zero ruff-check-fix autofixes on
any of the 13 files, only ruff-format-write.

Evidence: ran the full test files for both touched test modules
(tests/unit/test_ticket_runner_land_cmd_flags.py: 23 passed;
tests/unit/test_ticket_runner_land_release.py: 18 passed) plus a broader
src-side sweep covering the touched tickets/_land.py, _doable.py,
_new_renumber.py, _renumber_v2.py, _store_migrate.py, _unlanded.py,
app/ticket_runner/_verify.py, _cli_parsers/_ticket/_metadata.py modules
(tests/test_ticket_land.py + tests/unit/test_ticket_new_related.py +
tests/unit/test_unlanded_branch_work.py + tests/test_tickets.py: 533
passed, 0 failed). No pre-existing or reformat-induced failures found.

Filed: none -- no out-of-scope findings.
Gates: land-time gates run by frob ticket land; no waivers needed.

### Changed
```
 tickets/T-2813/ticket.md | 44 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 44 insertions(+)
```

### Evidence
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestAllowCrossTicketFlagParsing::test_flag_sets_the_namespace_dest` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestWriteReleaseBump::test_rewrites_version_and_prepends_changelog_entry` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 23 error(s), 1401 warning(s), 712 waived
- error-findings: AFFECT001@src/frob/tickets/_doable.py, AFFECT001@src/frob/tickets/_land_squash.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2790-check-stage-profile.md, DOC001@docs/investigations/T-2796-backlog-reproduction.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2813, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
