## Done report

Moved `_warn_if_native_stale` + `_maybe_rebuild_natives` out of the
staged-but-uncommitted window and behind the landing commit, via a new
private `_post_publish_native_rebuild` helper in
`src/frob/tickets/_land_squash.py`.

MEASURED, not asserted. The new must-fire fixture reverts to the parent
implementation and reports what the rebuild callback actually observed:

    AssertionError: the rebuild ran while root still held staged,
    uncommitted land content:
      'A  frob-core/src/lib.rs\nA  tickets-archive.md\nM  tickets.md'

That is three staged paths visible to every sibling process for the entire
duration of a cargo/maturin build. After the fix the same callback observes
`git status --porcelain` empty and `git rev-parse HEAD` equal to
`LandReport.commit_sha` -- a durable, committed, clean root.

ANSWER TO THE POST-PUBLISH FAILURE QUESTION (T-3101's real design
question): a rebuild failure after the commit is durable MUST be reported
and MUST NOT unwind, and the helper's docstring says so explicitly so a
later agent does not "harden" it into a revert. The commit is already
public and a sibling may already have stacked on it, so hard-resetting it
is the T-1456/T-1740 "reset --hard a real commit" hazard -- traded for a
strictly smaller problem: a stale local `.so`, which
`_warn_if_native_stale` and NATIVE001 already surface and a local
`frob natives build` already fixes. `_maybe_rebuild_natives` was already
best-effort and already logged loudly and returned `False`; this change
relocates that behavior without altering it, which is why the three
pre-existing `TestRebuildNatives` fixtures pass with zero edits.

The absorbed-sibling early return keeps calling the same helper, so a
stacked-absorption land rebuilds exactly as it did before -- the only
difference anywhere is when the build runs relative to the commit.

WHY THIS DID NOT WAIT FOR T-3101/T-3089: T-3101 specifies "after
`publish_ref_cas`", a call site that does not exist and is blocked behind
T-3089's re-scoped wiring. Today's publish point is
`_commit_squash_apply`, and the same move against it is a strict
improvement that needs no out-of-tree pipeline. When T-3089 lands, all
that remains in T-3101 is re-pointing this one call from after the commit
to after the CAS publish.

### Changed
```
 src/frob/tickets/_land_squash.py | 52 ++++++++++++++++++++++++++++++++++++----
 tests/test_ticket_land.py        | 52 ++++++++++++++++++++++++++++++++++++++--
 tickets/T-3111/ticket.md         |  7 +++++-
 3 files changed, 103 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestRebuildNatives::test_rebuild_runs_after_the_landing_commit_is_durable` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRebuildNatives::test_invoked_when_native_source_touched` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRebuildNatives::test_skipped_when_no_native_source_touched` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRebuildNatives::test_rebuild_failure_does_not_block_land` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 81 error(s), 1063 warning(s), 862 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC006@tickets/T-3109/ticket.md, DOC006@tickets/T-3110/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3111/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3111, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_land_compose.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py
