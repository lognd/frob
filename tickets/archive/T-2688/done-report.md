## Done report

Added COV008: a diff-time gate that refuses a diff which deletes or
renames a test file some ticket's evidence (open OR done) still cites,
when that evidence no longer resolves against the current collected set.
This is the diff-scoped complement to COV003 (which already catches an
already-broken citation, but only as a repo-wide, non-diff-scoped sweep
run later by an unrelated ticket -- discovered this session as the exact
root cause behind 4/4 of a prior measured error floor, and again as 6
closed tickets' evidence broken silently this session: T-1397/T-1526/
T-1688/T-2344/T-2348/T-2365).

Scope note update: the ticket's original declared scope
(src/frob/gates/_coverage.py) was a stale guess -- that module is
coverage.xml parsing/stamping/locking (TEST005/006/012), a documented
single-pipeline module (its own LARGE001/ARCH102 waivers say so
explicitly) and has never held any of the COV001..COV007 rule
implementations. Every sibling COV0XX rule lives in
src/frob/gates/__init__.py, alongside TicketQueue/CollectedTests/
Violation and the coverage_gate() dispatcher COV008 must be wired into
to run through the real production check path (required by this repo's
own T-0756 new-gate-rule acceptance policy). Scope was widened to
gates/__init__.py (deferred once for a live cross-worktree lease held by
T-2710, retried after T-2710 closed), gates/_waive.py (the shared
_KNOWN_GATE_RULES registry every rule id must be listed in), docs/
modules/gates.md (the rule catalog table + frob:enumerates directive +
a new COV008 prose section), tests/test_gates.py, and docs/design/
registry/check-coverage.yaml (REG010 requires a CHK-GATE-COV008 entry
for any new live rule; filed via `frob registry audit --sync-gate-rules`,
which also swept up one unrelated pre-existing gap, F401, in the same
pass).

## Positive controls (both required directions, both built and passing)

MUST-FIRE: test_cov008_fires_when_diff_deletes_a_cited_test -- a DONE
ticket cites tests/test_x.py::test_foo; the diff deletes tests/test_x.py;
COV008 fires naming the ticket and the evidence id. Designated as this
ticket's repro test (fails at the parent commit -- no COV008 rule exists
yet -- and passes after this change).

MUST-STAY-QUIET (both required shapes):
- test_cov008_silent_on_uncited_deletion: deleting a test file NO
  ticket's evidence cites (the overwhelming majority of ordinary test
  cleanup) -- silent, by construction (nothing in `changed` matches any
  evidence's file part).
- test_cov008_silent_on_rename_with_rebound_citation: a rename whose
  ticket evidence was ALREADY updated to the new node id -- the ticket's
  evidence no longer names the vanished old path at all, so there is
  nothing left for COV008 to match against the old path's disappearance,
  and the new id resolves fine against `tests`.

## Known residual gap (disclosed, not silently assumed covered)

COV008 runs as part of gate:COV, which IS invoked by `frob check`
including under `--ticket` scoping -- so any agent running `frob check`
before a land sees it. It does NOT yet force itself into the RAPID
land profile's synchronous pre-commit path: rapid profile skips the
pre-commit gate sweep entirely for speed (T-1575/T-1681/T-1684) and only
runs an async, non-blocking post-land sweep, which is what let the
6-ticket incident this session actually reach main uncaught even though
COV003 (COV008's non-diff-scoped ancestor) already existed. Making
COV008 specifically block a rapid-profile land synchronously is a
separate, larger land-path change (src/frob/tickets/_land.py /
_rapid_sweep.py, well outside this ticket's gates/__init__.py scope) and
is NOT attempted here -- flagged as a residual gap, not assumed solved.

## Done report

Changed:
- src/frob/gates/__init__.py::_diff_deleted_or_renamed_paths (new)
- src/frob/gates/__init__.py::_cov008_violation (new)
- src/frob/gates/__init__.py::_cov008 (new)
- src/frob/gates/__init__.py::coverage_gate (wired COV008 in)
- src/frob/gates/_waive.py::_KNOWN_GATE_RULES (added COV008)
- docs/modules/gates.md (rule table row, frob:enumerates member, new
  "COV008 (T-2688)" section)
- docs/design/registry/check-coverage.yaml (CHK-GATE-COV008 +
  CHK-GATE-F401 entries via frob registry audit --sync-gate-rules)
- tests/test_gates.py (3 new TestCoverageGate tests)
Evidence:
- tests/test_gates.py::TestCoverageGate::test_cov008_fires_when_diff_deletes_a_cited_test (designated repro; bound to acceptance[0])
- tests/test_gates.py::TestCoverageGate::test_cov008_silent_on_uncited_deletion (bound to acceptance[0])
- tests/test_gates.py::TestCoverageGate::test_cov008_silent_on_rename_with_rebound_citation (bound to acceptance[0])
Filed: none
Gates: `frob check --ticket T-2688 --only gates-fast` measured directly;
all COV008/REG009/REG010 findings cleared after the registry sync. The
full TestCoverageGate class (77 tests) and tests/gates/test_rule_id_scan_branches.py
(20 tests) pass. Remaining FAIL families (DOC/DRIFT/TICK/WAIVE/REF/REL/
SUPPRESS/PRE) are pre-existing repo-wide baseline per the run's own
NOTE line, not introduced by this change -- spot-checked REG005/REG002/
REG008's residual findings (VERSION001/TDD001/VMOD001/NARR001 disposition
gaps) and confirmed none of them name COV008 or F401.

### Changed
```
 docs/design/registry/check-coverage.yaml |  12 +++-
 docs/modules/gates.md                    |  29 ++++++++-
 src/frob/gates/__init__.py               | 101 ++++++++++++++++++++++++++++++-
 src/frob/gates/_waive.py                 |   4 ++
 tests/test_gates.py                      |  92 ++++++++++++++++++++++++++++
 tickets/T-2688/ticket.md                 |  59 +++++++++++++++++-
 6 files changed, 292 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageGate::test_cov008_fires_when_diff_deletes_a_cited_test` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov008_silent_on_uncited_deletion` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov008_silent_on_rename_with_rebound_citation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 75 error(s), 1611 warning(s), 878 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@.claude/hooks/frob-suggest.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2688/src/frob/gates/__init__.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2688, REF002@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_narrative_migrate.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
