## Done report

Confirmed the reported defect reproduces on current main (AssertionError
accessing frob.app.profile_runner_run). Added the missing
'elif module_name == "profile_runner"' branch to
_import_runner_run_module's closed if/elif chain, and added an exhaustive
regression test (test_every_registered_runner_run_alias_resolves) that
walks every _RUNNER_RUN_MODULES entry instead of spot-checking one alias,
per the ticket's suggestion, so a future addition to the dict without a
matching chain branch fails immediately.

Evidence: the new test fails with the original AssertionError before the
fix and passes after (fail-then-pass, not confirmatory-only).
frob test --base main recorded 4 python test outcomes, exit=0.

Verified with frob check --ticket T-4297 --json (unscoped): dropped from
15 to 8 errors after fixing COV002 (missing frob:ticket edge), DUP001 (x5,
waived -- repetition required by T-1337's literal-import design, out of
this ticket's scope to refactor), OPAQUE001 in the new test (waived --
the dynamic getattr over the closed dict is the point of the exhaustive
test), and a stale pre-work sweep / line-length wrap on the waiver
comment. The remaining 8 errors (ARCH103 in src/frob/graph/cache.py,
SELFAUDIT001 on design:1 claude_hooks capability declarations, WIRE002 in
tests/test_ci_workflow_timeout.py) are pre-existing and unrelated to this
ticket's files -- confirmed by path, not touched or waived here.

Filed: none -- no out-of-scope defect discovered while working this
ticket.

### Changed
```
 tickets/T-4297/done-report.md | 39 +++++++++++++++++++++++++++++++++++++++
 tickets/T-4297/ticket.md      |  2 ++
 2 files changed, 41 insertions(+)
```

### Evidence
- `tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_every_registered_runner_run_alias_resolves` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 3 error(s), 4652 warning(s), 954 waived
- error-findings: ARCH103@src/frob/graph/cache.py, SELFAUDIT001@design, WIRE002@tests/test_ci_workflow_timeout.py
