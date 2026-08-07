## Done report

Changed:
- tests/test_ticket_land.py (18 new test methods across 6 new test
  classes: TestCloseFailAfterMerge, TestLandNotFound,
  TestGitSubprocessFailures, TestLandDeeperBranches, plus additions to
  existing TestWipCommit/TestKindEvidenceMismatch/
  TestUnownedDeletionRealRun/TestMergeConflictOutsideLedger)
- tests/test_tickets_cmd_evidence.py (3 new tests: OSError launch
  failure, ticket-not-found load propagation, write-failure propagation)
- tests/unit/strata/test_lint.py (7 new test classes covering
  `_rate_base` unit-mismatch branches, LINT002/LINT005 dimension-error
  propagation, `_scenario_touched_nodes`'s missing-flow branch,
  `_scenario_has_bound_claim`'s non-matching-body branches, fan-in's
  no-rated-inbound early continue, and evaluate_lint's per-rule
  short-circuit propagation)
- tests/test_capability_registry.py (new TestIsSelfPatternPath class,
  6 tests covering the root/self/foreign/OSError discriminator branches)
- tests/unit/test_dup_cache.py (2 new tests: cache-hit overwrite via
  INSERT OR REPLACE, connect-error short-circuit)

No src/ files touched; scope stayed within tests/**, tickets.md, and the
5 declared src/ paths (read-only reference).

Evidence: 22 pytest node ids recorded via `frob ticket evidence` (see
`evidence:` list above), all independently verified passing:
`uv run python -m pytest tests/test_ticket_land.py
tests/test_capability_registry.py tests/test_tickets_cmd_evidence.py
tests/unit/strata/test_lint.py tests/unit/test_dup_cache.py -o
addopts="-q"` -> 444 passed.

TEST005 before (this ticket's 6 target functions, `uv run frob check
--only test`):
```
src/frob/tickets/_land.py::land branch coverage 71.0% (below 90%)
src/frob/tickets/_land.py line coverage 72.7% (below 85%)
src/frob/tickets/__init__.py::run_cmd_evidence branch coverage 75.0%
src/frob/tickets/__init__.py::add_cmd_evidence branch coverage 89.5%
src/frob/strata/_lint.py::evaluate_lint branch coverage 76.9%
src/frob/strata/_lint.py::check_lint_fanin_capacity branch coverage 87.5%
src/frob/vet/_capability.py::is_self_pattern_path branch coverage 77.8%
src/frob/dup/_cache.py::put_fingerprint branch coverage 87.5%
```
TEST005 after (same command, same 6 functions/files): ZERO unwaived
TEST005 entries for any of the 5 target files (`land()` reached 90%+
branch / 85%+ line; the other 5 functions reached full statement+branch
coverage for their own bodies -- confirmed by grepping the gate output
for these 5 file paths and finding no un-waived TEST005 line). One
genuinely dead branch was found and left uncovered rather than forced:
`evaluate_lint`'s `return Err(rate.danger_err)` after
`check_lint_rate_limit` (line 406) -- `check_lint_rate_limit` has no
fallible sub-call and always returns `Ok(...)`; there is no input that
reaches that `Err` arm.

Filed: none (no out-of-scope work found).

Gates: `uv run frob check --ticket T-draft-5321d1bc` clean, 0 errors
(after re-running `frob ticket sweep T-draft-5321d1bc` to refresh the
stale pre-work sweep). Full-repo `uv run frob check` (unscoped): 0
errors, 15 warnings, 223 waived (pre-existing, unrelated to this
ticket's scope). `make coverage` clean, all tests pass. `ruff check` and
`uv run ruff check` both clean; `ruff format`/`uv run ruff format`
clean on all 5 touched test files; `ty` clean (fixed one pre-existing-in-
this-diff Err[TicketError] invalid-subscript return annotation in
tests/test_tickets_cmd_evidence.py to `Result[object, TicketError]`).
`git diff main --diff-filter=D --stat` empty. No non-ASCII characters.
No Cargo.lock churn.
