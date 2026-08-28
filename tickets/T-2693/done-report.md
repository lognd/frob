## Done report

PREMISE CHECK -- STALE: the standing TICK006 finding this ticket describes
(T-2685's phantom citation of T-draft-be1e79b5 colliding with T-2689's
identical title/scope, tainting every unrelated land that touches
tickets.md) no longer exists on current main.

Measured directly: `frob check --only tickets` on this worktree reports
exactly one live TICK006 finding, and it names a DIFFERENT ticket/draft
pair entirely (T-3031/T-draft-36006d55) -- there is no TICK006 finding
naming T-2685, T-2689, or T-draft-be1e79b5 anywhere in tickets.md.

Root cause: this exact defect class (the git-rename-lookup-based TICK006
Tier-A auto-fix refiling a duplicate instead of resolving the draft id via
its recorded rename) was already fixed for this specific
T-2685/T-draft-be1e79b5 case by the T-2690 -> T-2699 -> T-2701 -> T-2702
chain:
- T-2690 first tried to add git-rename resolution to
  fix_tick006_phantom_refile, but the fix was not actually reachable on
  the real land path (T-2702's own investigation: two more duplicate
  refiles, T-2699 and T-2701, were filed by lands PROVABLY containing
  T-2690's commit).
- T-2702 (DONE, land_commit=e983c75cdbbc74601a056fcb5d123b1a68412907)
  found and fixed the real invocation gap in
  src/frob/gates/_fix_engine.py / src/frob/app/ticket_runner/_land_cmd.py,
  with evidence including
  tests/test_gates.py::TestFixEngineTierA::test_tick006_two_lands_citing_same_draft_produce_at_most_one_ticket
  (the designated repro), directly covering "two lands citing the same
  phantom draft produce at most one ticket" -- the exact shape T-2693
  describes.
- T-2689 itself is `state: dropped` (2026-08-19, pre-dating this ticket's
  2026-08-19 filing time too) with a Drop reason citing the same git-
  rename resolution (T-draft-be1e79b5 -> T-2678 via commit a44f96e60),
  so it carries no open scope/title for a future refile to collide with
  even if the phantom-refile Tier-A fix fired again today.

No code change was needed or made. Verified no other stale-finding
residue: `tickets.md` has zero TICK006 lines naming T-2685/T-2689/
T-draft-be1e79b5, and both T-2685 and T-2689 are archived in terminal
states (done / dropped respectively).

## Done report

Changed: none (investigation-only; premise already resolved by T-2702)
Evidence: tests/test_gates.py::TestFixEngineTierA::test_tick006_two_lands_citing_same_draft_produce_at_most_one_ticket
(T-2702's own designated repro test for this exact "two lands cite the
same phantom draft" shape; re-cited here since T-2693 needed no new code)
Filed: none
Gates: `frob check --only tickets` measured directly -- 6 errors none of
which name T-2685/T-2689/T-draft-be1e79b5 (the one live TICK006 finding
is an unrelated T-3031/T-draft-36006d55 pair); the specific finding this
ticket exists to fix is absent, confirming the premise is stale.

### Changed
```
 tickets/T-2693/ticket.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 72 error(s), 683 warning(s), 878 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@.claude/hooks/frob-suggest.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_narrative_migrate.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
