## Done report

Changed (13 files, format-only, `frob format` per-file):
tests/test_tickets_body.py
tests/test_tickets_cmd_evidence.py
tests/test_tickets_collision.py
tests/test_tickets_dispatch_stale.py
tests/test_tickets_ledger_concurrency.py
tests/test_tickets_live_tracker.py
tests/test_tickets_migration.py
tests/test_tickets_milestone_runs_last.py
tests/test_tickets_milestone_sort.py
tests/test_tickets_parent.py
tests/test_tickets_review.py
tests/test_tickets_scope_mutation.py
tests/test_waive_gate.py

File-selection note: picked from the 58 files `ruff format --check .`
reported remaining after batch 11 (T-2808), with fresh leases re-pulled
per the coordinator's updated guidance rather than reusing the prior
snapshot -- `scripts/fleet_status.py` plus `.git/frob-leases/*.json` for
every live entry (T-2370, T-2373, T-2755, T-2805, T-2806) checked before
picking, not after. T-2373's own recorded lease scope is currently empty
(`[]`, the epic-rollup shape), but per the coordinator's explicit warning
its historical child claimed 12 tests/ files including several still in
the remaining-58 pool -- excluded all 6 that still appear there
(test_ticket_land.py, test_ticket_work_and_land_finish.py,
test_tickets_organization.py, test_tickets_priority.py,
unit/test_app_runners_batch6.py, unit/test_app_runners_t2395_contention.py)
as a precaution rather than trusting the momentarily-empty lease. Also
excluded tests/unit/test_check.py (T-2806's declared scope, live).
`frob ticket start` accepted this batch's scope with zero lease
collisions on the first try.

Diff reviewed by hand across all 13 files: pure line-wrap reformatting,
one docstring quote-escape normalization (test_tickets_milestone_sort.py:
`""""1.10.0"` -> `" "1.10.0"` spacing) and one raw-vs-single-quoted
string-literal normalization (test_waive_gate.py), no logic changes, no
fixture-corpus file in the diff. `frob format` needed zero ruff-check-fix
autofixes on any of the 13 files, only ruff-format-write.

Evidence: 13 pytest node ids bound, one per touched file.
Full-batch run: `uv run pytest -n 4` across all 13 files -- 282
collected, 0 failed.

Filed: this is child batch 12 of T-2359 (parent epic-tracking ticket,
still open pending further batches; 58 -> 45 files remaining after this
batch).

Gates: `frob format` applied ruff-format-write only (no autofixes) per
file; diff reviewed by hand, no semantic changes.

### Changed
```
 tickets/T-2811/ticket.md | 55 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 55 insertions(+)
```

### Evidence
- `tests/test_tickets_body.py::TestBodyAmend::test_append_appends_text` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestIsCmdEvidence::test_shapes` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestPostArchiveReissueIncident::test_new_ticket_never_reissues_an_archived_id` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_live_lease_is_in_flight` (pytest node id, verified passing when recorded)
- `tests/test_tickets_ledger_concurrency.py::TestArchiveRaceWithConcurrentNew::test_concurrent_new_ticket_survives_a_racing_archive` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_empty_repo_has_no_citations` (pytest node id, verified passing when recorded)
- `tests/test_tickets_migration.py::TestMigrateV1ToV2::test_migrates_one_active_ticket_with_done_report` (pytest node id, verified passing when recorded)
- `tests/test_tickets_milestone_runs_last.py::TestRunsLastMilestoneScoping::test_unmilestoned_runs_last_keeps_global_semantics` (pytest node id, verified passing when recorded)
- `tests/test_tickets_milestone_sort.py::TestEffectiveMilestone::test_own_milestone_is_declared` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParent::test_reparents_leaf_to_epic` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestRecordReview::test_appends_approve_entry` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestScopeLeaseConflict::test_no_collision_is_none` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_pending_phrasing_is_binding` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: 19 error(s), 1020 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2790-check-stage-profile.md, DOC001@docs/investigations/T-2796-backlog-reproduction.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
