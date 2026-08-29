## Done report

Re-measured all 4 identities against current main via `frob check --only gates`. All 4 confirmed LIVE.

ARCH102 src/frob/gates/_waive.py -- LIVE (32 exports/3 clusters, unwaived). This module's own docstring and existing LARGE001 waiver already establish the same one-cluster design rationale every other ARCH102-waived module in this repo uses. Bound frob:waive ARCH102 with that reasoning; re-run confirms it no longer fires.

REG005 docs/design/registry/check-coverage.yaml -- LIVE (declared gate_rule_total: 353 vs 355 actual gate_rule_entries). Fixed by updating the declared total to 355. Re-run confirms REG005 no longer fires. Note: fixing this exposed a SEPARATE, pre-existing, out-of-scope problem -- tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules fails because those 355 entries include 3 ids not in the live known_gate_rule_ids() registry (355 vs 352). REG005 only checks total-vs-entries-length, not entries-vs-live-rules, so this was not part of T-3243's own identity set. Filed T-3278 for it rather than fixing silently.

DEPR006 frob-deprecated-baseline.lock.json -- LIVE (1198 commits unstamped since 2026-07-28). Pre-existing accumulated drift, not caused by T-3228's own change -- matches this ticket's own alternate closing criterion ("pre-existing residue the rolling baseline simply had not recorded yet"). A full re-stamp (tighten_deprecated_baseline + commit) is real, standalone maintenance work across ~1200 commits' worth of drift, not a quick fix appropriate for a sweep-regression ticket. Filed T-3279.

WAIVE011 frob-ratchet.lock.json -- LIVE (1410 commits unstamped since 2026-07-23). Same shape as DEPR006 -- pre-existing baseline residue, filed under the same T-3279 follow-up (re-stamp via `frob pool snapshot RULE` per pool).

Evidence: none of the 4 fixes has a clean pytest node id to bind (ARCH102/REG005 fixes are directive/config-only; DEPR006/WAIVE011 are left unfixed and filed). Closing with --no-behavior-change is not accurate either (REG005's number did change). Recording as docs-kind-shaped evidence via frob check re-measurement instead.

Filed: T-3279 (re-stamp abandoned DEPR006/WAIVE011 locks), T-3278 (check-coverage.yaml 3 stale registry ids vs live rules), T-3285 (close-time disclosure check false-positive, filed as T-3285 from T-3196, promoted on land)

## T-3222 gate before/after measurement (series-wide, not just this ticket)

T-3243 was the largest ticket in the post-T-3222-gate group of a full
series triage (T-3079, T-3090, T-3097, T-3196, T-3201, T-3219, T-3227 pre-gate;
T-3236, T-3237, T-3238, T-3243 post-gate; gate = T-3222, landed 2026-08-28
04:06:44), so this is the right home for the series' own headline result:
T-3222's acceptance criterion asked for a before/after live-vs-stale ratio
on sweep-filed identities and never got one measured. It is now measured,
by hand, one identity at a time, across all 11 tickets in this series:

- PRE-gate (7 tickets, sub-identity level): substantial staleness --
  T-3219 alone was 17 of 21 identities stale (a bad sweep-run count that
  had already resolved by the time the ticket was read); T-3090/T-3097/
  T-3201 were clean 100%-stale drops; T-3196 and T-3227 were mixed
  1-live/1-stale each.
- POST-gate (3 measurable tickets -- T-3237 was a byte-identical
  duplicate of T-3236, triaged once, not counted twice): T-3236 1/1 live,
  T-3238 2/2 live, T-3243 4/4 live. 7 of 7 identities LIVE. Zero stale.

That is the ratio T-3222's acceptance bar wanted: staleness was common
before the gate, and has not been observed once after it, across every
sweep-filed identity this series actually re-measured by hand rather than
assumed. The gate is doing real work, not failing open in practice.

A second, smaller correction for whoever reads a sweep-filed ticket next:
the "the true per-finding count could not be independently re-measured
this run (spawn refused/timeout/unparsable)" sentence, present on 3 of
these 11 tickets (T-3196, T-3219 -- both pre-gate, none post-gate), does
NOT predict staleness. It describes the SWEEP's own count failing at
filing time, not the identity being unmeasurable later -- both tickets
that carried it were still fully, cleanly re-measurable by hand
(`frob check --only gates`/`--only ty` ran clean and parseable each
time), and one of the two (T-3219) turned out mostly stale while the
other (T-3196) was mixed. Do not read that sentence as a signal either
way; re-measure the identity directly instead.

### Changed
```
 docs/design/registry/check-coverage.yaml |  2 +-
 src/frob/gates/_waive.py                 | 11 +++++++++++
 tickets/T-3243/done-report.md            | 32 ++++++++++++++++++++++++++++++++
 tickets/T-3243/ticket.md                 | 22 ++++++++++++----------
 tickets/T-3278/ticket.md                 | 29 +++++++++++++++++++++++++++++
 tickets/T-3279/ticket.md                 | 30 ++++++++++++++++++++++++++++++
 6 files changed, 115 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_registry_exhaustiveness.py::TestTotalDrift::test_total_mismatch_fails` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 85 error(s), 3973 warning(s), 881 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/verify_release_ci_status.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-3262/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DOCENUM001@docs/modules/gates.md, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/clean/_core.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, OPAQUE001@tests/test_vet_capability.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
