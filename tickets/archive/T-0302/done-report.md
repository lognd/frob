## Done report

Changed:
- tests/unit/strata/test_selfconform.py::TestBindingErrorPropagation::test_ambiguous_code_binding_propagates_as_err
- tests/unit/strata/test_host_isolation.py::TestHostIsolationWaivers::test_propagates_lateral_isolation_error
- tests/unit/strata/test_host_isolation.py::TestHostIsolationWaivers::test_propagates_vertical_isolation_error
- tests/test_ticket_land.py::TestSpliceLedger::test_malformed_ours_propagates_as_err
- tests/test_ticket_land.py::TestSpliceLedger::test_malformed_theirs_propagates_as_err

Per-function branch coverage, before -> after (`make coverage` then
`uv run frob check --only test`):
- src/frob/strata/_selfconform.py::check_self_conformance: 87.5% -> 100%
  (added a two-node overlapping-`code=`-glob case that drives `bind_code`
  to `Err(AmbiguousCodeBinding)`, exercising the `bound_binding.is_err`
  branch at line 471-472; propagation asserted via `result.danger_err`).
- src/frob/strata/_host_isolation.py::evaluate_host_isolation_waived:
  80.0% -> 100% (monkeypatched `evaluate_lateral_isolation` and
  `evaluate_vertical_isolation`, each independently, to return
  `Err(StrataError.UnknownReference)` -- neither delegate can produce an
  `Err` given the current HOST001/HOST002 implementation, so this is the
  only way to exercise the `lateral.is_err`/`vertical.is_err` propagation
  branches at lines 811/814; both assert the error surfaces unchanged and
  that HOST002 never runs after a HOST001 failure).
- src/frob/tickets/_land.py::splice_ledger: 83.3% -> 100% (a malformed
  `ours_text`/`theirs_text` -- a `<!-- ticket:T-... -->` marker with no
  ```yaml frontmatter -- drives `_parse_ledger` to `Err`, exercising both
  the `ours_parsed.is_err` branch at line 96-97 and the
  `theirs_parsed.is_err` branch at line 99-100 independently).

Evidence: recorded node-level via `frob ticket evidence` (5 ids above),
each collected from a fresh `pytest --collect-only` pass in a
`make core`-built worktree.

Filed: none (all three gaps were closeable within the ticket's declared
`tests/**` scope; no out-of-scope structural issue was found).

Gates:
- `make coverage` then `uv run frob check --only test`: 0 errors,
  0 warnings, 181 waived (all three target TEST005 warnings for
  `check_self_conformance`, `evaluate_host_isolation_waived`, and
  `splice_ledger` no longer appear in output; no new warnings
  introduced).
- `uv run frob check` (full): `gates 0 errors, 0 warnings, 205 waived`.
- `uv run pytest tests/unit/strata/test_selfconform.py
  tests/unit/strata/test_host_isolation.py tests/test_ticket_land.py -q`:
  all green (0 failures).
- `uv run ruff check` and `ruff check` (both PATH and project-pinned) on
  the three touched test files: "All checks passed!" under both.
- `uv run ty check` on the three touched test files: "All checks passed!".
- `git diff main --diff-filter=D --stat`: empty (deletion-filter clean).

Not closing this ticket -- leaving for reviewer per the review-gated
workflow (playbook section 11).
