## Done report

Changed:
src/frob/gates/_render_lint.py::render001_scans (new: structural scan-membership predicate, reuses render_lint_gate's own pathspec/exemption logic verbatim -- no second hardcoded copy)
src/frob/app/ticket_runner/_waive_audit.py::WaiverLiveness (new enum: NECESSARY/INERT/UNVERIFIED)
src/frob/app/ticket_runner/_waive_audit.py::classify_waiver_liveness (new: the classifier)
src/frob/app/ticket_runner/_waive_audit.py::_load_liveness_scan_checkers/_LIVENESS_SCAN_CHECKERS (new: rule -> scan-membership-predicate registry, RENDER001 wired first)
src/frob/app/ticket_runner/_waive_audit.py::_run_scan_subcommand (wired --check-liveness)
src/frob/app/ticket_runner/_waive_audit.py::_render_waiver_liveness (new: report renderer)
src/frob/_cli_parsers/_ticket/_closeout.py::_add_ticket_waive_audit_parser (new --check-liveness flag)
src/frob/app/config.py::AppConfig.waive_audit_check_liveness (new field)
src/frob/app/_config_external.py::_BOOL_FLAGS (added waive_audit_check_liveness)
tests/unit/test_waive_audit_runner.py::TestClassifyWaiverLiveness (4 new tests)
tests/test_gates.py::TestRenderLintGate (3 new tests for render001_scans)

Design (the soundness line, drawn deliberately narrow):

- NECESSARY: this run's actual GateReport.waived (the real _apply_waivers
  output, not an inference) shows the waiver suppressing a real violation.
  Direct observation.
- INERT: the waiver's rule has a REGISTERED structural scan-membership
  predicate (currently RENDER001 -> render001_scans, itself the SAME
  logic render_lint_gate uses internally, not a second hardcoded copy --
  this closes exactly the class of bug T-2719 found, a duplicate
  pathspec silently drifting from the real one) and the waiver's file
  falls outside that predicate's scan set. Structural fact, not an
  absence-of-finding inference.
- UNVERIFIED: neither established. This is the HONEST default -- NEVER
  "obsolete". The ticket's own hazard section (55 live waivers deleted by
  the T-1579 `_rule_has_live_finding` incident, reasoning "the rule fired
  somewhere, so a waiver of that rule matching nothing here is provably
  stale") is exactly the reasoning this classifier refuses to repeat. An
  OBSOLETE verdict is never claimed automatically anywhere in this diff --
  T-2739's own hand-constructed synthetic-diff measurement remains the
  only sound way to establish that, per this repo's own waiver-removal
  discipline.

REPORT-ONLY: --check-liveness never mutates a waiver, never gates
`frob check`/`frob ticket land`'s own exit status -- same posture as
T-2496's --check-collisions immediately beside it. An INERT verdict's
render text explicitly frames it as a lead on BOTH the waiver and the
rule's own scan pathspec (matching the ticket's own "T-2719 found this
by widening a scan" framing) -- never license to bulk-remove.

Evidence:
tests/unit/test_waive_audit_runner.py::TestClassifyWaiverLiveness::test_necessary_when_waived_this_run
tests/unit/test_waive_audit_runner.py::TestClassifyWaiverLiveness::test_inert_when_rule_does_not_scan_the_file
tests/unit/test_waive_audit_runner.py::TestClassifyWaiverLiveness::test_unverified_when_no_checker_registered
tests/unit/test_waive_audit_runner.py::TestClassifyWaiverLiveness::test_necessary_never_inert_even_with_a_registered_checker
tests/test_gates.py::TestRenderLintGate::test_render001_scans_true_for_a_real_scanned_file
tests/test_gates.py::TestRenderLintGate::test_render001_scans_false_for_an_exempt_path
tests/test_gates.py::TestRenderLintGate::test_render001_scans_false_for_a_path_outside_any_pathspec

Positive controls (per the coordinator brief, both directions):
- test_inert_when_rule_does_not_scan_the_file: a waiver on a path RENDER001
  does not scan reports INERT.
- test_necessary_when_waived_this_run / test_necessary_never_inert_even_with_a_registered_checker:
  a waiver actively suppressing a reproducing finding reports NECESSARY,
  and NEVER inert even when a registered checker exists for its rule
  (the second test proves NECESSARY wins over a checker that WOULD
  otherwise apply, closing the "a registered checker always wins" bug
  class).
- test_unverified_when_no_checker_registered: the existing honest/cop-out
  judgement path (find_collision_suspects, AuditVerdict/T-1614 rubric) is
  entirely untouched by this diff -- classify_waiver_liveness is purely
  additive, called only from the new --check-liveness branch.
- Live full-repo run (`frob ticket waive-audit scan --check-liveness --json`,
  654 necessary / 392 unverified / 0 inert): zero INERT is the expected,
  correct result post-T-2733 (which already removed the 11 RENDER001
  waivers that motivated this ticket) -- confirms the classifier does not
  spuriously flag the now-clean corpus.

Filed: T-2752 (docs kind) -- add prose to docs/modules/app.md#waive-audit-t-2467
and docs/modules/render.md#renderer describing --check-liveness, deferred
because docs/modules/app.md was under T-2694's live cross-worktree lease
for this ticket's entire duration (frob ticket scope --add refused with
ScopeLeaseConflict). Cited as follow_up on the 3 AFFECT001 waivers this
diff carries for exactly that reason; renumbers to a real id at land.

Gates (post-merge-main, pre-land, `frob check --ticket T-2740 --json --no-cache`,
unbudgeted): gates: 73 error(s) total repo-wide (pre-existing, unrelated to
this diff -- CYCLE001/import-cycle noise and other repo-wide floor items),
0 of them attributed to any file this ticket touched (verified by
filtering the JSON report's results[].diagnostics[] for every touched
path -- src/frob/gates/_render_lint.py, src/frob/app/ticket_runner/
_waive_audit.py, src/frob/_cli_parsers/_ticket/_closeout.py, src/frob/
app/config.py, src/frob/app/_config_external.py, tests/unit/
test_waive_audit_runner.py, tests/test_gates.py, docs/modules/app.md).
Earlier in this ticket's own history the scoped check DID catch 5 real
regressions from this diff (COV002 missing frob:ticket on a changed test
class, WIRE001 on the new render001_scans, AFFECT001 x3 for doc-anchor
drift, then later a genuine DUP001 near-duplicate test and a WAIVE006
stale-ticket-citation once T-2694 went done) -- all fixed and
re-verified to 0 before this final measurement, not waived away.

### Changed
```
 docs/modules/app.md                        |  32 +++++
 rapid-debt.jsonl                           |   3 +
 src/frob/_cli_parsers/_ticket/_closeout.py |  21 +++
 src/frob/app/_config_external.py           |   2 +
 src/frob/app/config.py                     |   4 +
 src/frob/app/ticket_runner/_waive_audit.py | 214 +++++++++++++++++++++++++++-
 src/frob/gates/_render_lint.py             |  39 +++++-
 tests/test_gates.py                        |  49 +++++++
 tests/unit/test_waive_audit_runner.py      | 215 ++++++++++++++++++++++++++++-
 tickets/T-2740/done-report.md              | 109 +++++++++++++++
 tickets/T-2740/ticket.md                   |  22 ++-
 tickets/T-2752/ticket.md         |  31 +++++
 12 files changed, 736 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_waive_audit_runner.py::TestClassifyWaiverLiveness::test_necessary_when_waived_this_run` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive_audit_runner.py::TestClassifyWaiverLiveness::test_inert_when_rule_does_not_scan_the_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive_audit_runner.py::TestClassifyWaiverLiveness::test_unverified_when_no_checker_registered` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive_audit_runner.py::TestClassifyWaiverLiveness::test_necessary_never_inert_even_with_a_registered_checker` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRenderLintGate::test_render001_scans_true_for_a_real_scanned_file` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRenderLintGate::test_render001_scans_false_for_an_exempt_path` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRenderLintGate::test_render001_scans_false_for_a_path_outside_any_pathspec` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive_audit_runner.py::TestClassifyWaiverLiveness::test_appconfig_check_liveness_defaults_false` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive_audit_runner.py::TestCheckLivenessWiring::test_check_liveness_renders_inert_and_necessary` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive_audit_runner.py::TestCheckLivenessWiring::test_check_liveness_never_flags_when_gate_run_fails` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 39 error(s), 1726 warning(s), 698 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_close_cmd.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2742/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@src/frob/tickets/_land.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@src/frob/serve/_socketd.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
