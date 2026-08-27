## Done report

Changed:
- docs/strata/vmodel.md -- "The four closure rules" -> "The five closure
  rules": rules 1 and 2 now describe the T-3043 fix (the backward/forward
  closure must actually REACH a real boundary-level node -- innermost for
  rule 1, outermost for rule 2 -- a non-empty closure is no longer
  sufficient), and a new rule 5 (check_no_trace_cycle, the acyclicity
  check over satisfies/refines/allocates via the kernel's existing
  find_cycle) is documented.
- strata-core/src/graph/vmodel.rs -- the 7 frob:doc anchor comments
  pointing at docs/strata/vmodel.md#the-four-closure-rules-t-3004-section-2
  updated to the new #the-five-closure-rules-t-3004-section-2 slug (the
  heading rename would otherwise break DOCANCHOR resolution). Mechanical
  anchor-string change only, no logic touched. Scope widened from the
  ticket's declared docs/strata/vmodel.md to include this file, narrowly,
  with a reason recorded via `frob ticket scope --reason`.

Narrative and justification stay in this ticket per the owner's standing
instruction; the doc itself only states the implemented behaviour.

Evidence: tests/unit/strata/test_vmodel_check.py -- 7/7 passing,
unaffected by this doc/anchor-only change (this is the existing
integration coverage for the vmodel module the anchors point into; a
docs-only change has no pytest surface of its own per playbook sec 5).

Verification commands run:
  uv run frob check --ticket T-3056 --only docanchor
  uv run frob check --ticket T-3056 --only doclink
    -> both show the same repo-wide pre-existing DOC/DRIFT/WAIVE findings
       (logging_module.py DRIFT002s, unrelated WAIVE010 reason-wording
       findings); zero findings reference vmodel.md or vmodel.rs.
  git diff main --diff-filter=D --stat -> empty
  uv run pytest -q tests/unit/strata/test_vmodel_check.py
    -> SUITE-RESULT exitstatus=0 collected=7 failed=0
  uv run pytest -q tests/unit/strata/test_vmodel_authoring.py::TestVmodelAuthoringFormat::test_vmodel_node_and_edge_round_trip_through_python
    (both on this worktree and on main, unmodified) -> same pre-existing
    failure (an unrelated attrs-field schema mismatch, T-3044-era), not
    caused by this change.

Filed: none new.
Gates: frob check --ticket T-3056 --only docanchor/doclink clean of any
vmodel-attributable finding; all remaining errors/warnings are pre-
existing repo-wide debt unrelated to this diff.

### Changed
```
 docs/strata/vmodel.md           | 41 ++++++++++++++++++++++++++++++-----------
 strata-core/src/graph/vmodel.rs | 14 +++++++-------
 tickets/T-3056/ticket.md        | 11 ++++++++++-
 3 files changed, 47 insertions(+), 19 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 63 error(s), 656 warning(s), 861 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3066/ticket.md, DOC006@tickets/T-3069/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3056, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py
