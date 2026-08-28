## Done report

DETERMINATION (per acceptance): both measured cases were EXAMINED and
REJECTED by attribute_batch, not never-considered -- both tickets'
bodies already showed "candidate commits: []" from a real reachability
run. T-2929's stale-baseline refusal does NOT apply to either case: it
gates a different call site (_check_claim_divergence_post_land's reuse
of rapid_soft_warning), never attribute_batch/_attribute_new_findings,
which runs unconditionally against the current verify queue. This is a
reachability-direction bug, not a baseline-freshness problem.

Root cause: _matching_batch_entries only checked forward reachability
(touched symbol reaches finding symbol via caller->callee edges). Both
measured findings are the INVERSE shape: a commit changed a callee's
signature/contract (touched), and the finding is at a stale CALLER
(target) that still calls it the old way. The call edge runs
target->touched, the opposite direction from what was checked, so
forward-only reachability structurally could not see it.

Fix: added a reverse-direction fallback (target reaches touched),
tried ONLY when the forward check finds zero matches for a given
finding -- never merged into one combined check. Trying both directions
unconditionally was attempted first and reverted: it regressed a
pre-existing clean single-attribution test into a false ambiguity,
because a finding's code routinely calls other symbols some unrelated
batch commit also happens to have touched, and unconditional reverse
checking turned that coincidence into a spurious extra "candidate".
Falling back only on a forward zero keeps every previously-clean
attribution byte-for-byte unchanged while recovering exactly the class
of miss both measured cases hit.

T-2929: untouched. Its own must-fire/must-stay-quiet tests
(tests/unit/test_rapid_sweep.py, the T-2929-tagged staleness cases)
still pass unmodified, confirming the stale-baseline refusal still
fires and this change did not relax it.

Gates: frob check --ticket T-3179 -- zero SCOPE/PREWORK diagnostics
(the families --ticket actually scopes); the 22 repo-wide errors in
that run are pre-existing native-module/ty findings unrelated to this
change (frob_core/strata_core unresolved imports, an import cycle, a
test's positional-arg call shape) -- confirmed present before this
ticket's edit by symbol/file, none touching src/frob/verify/_attribution.py
or tests/unit/verify/test_attribution.py.

Filed: none -- both measured cases share one root cause and are fixed
by one change.

### Changed
```
 src/frob/verify/_attribution.py       | 93 +++++++++++++++++++++++++++++++----
 tests/unit/verify/test_attribution.py | 91 ++++++++++++++++++++++++++++++++++
 2 files changed, 175 insertions(+), 9 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 74 error(s), 795 warning(s), 880 waived
- error-findings: AFFECT001@src/frob/verify/_attribution.py, ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@.claude/hooks/frob-suggest.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3179, REF002@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_narrative_migrate.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
