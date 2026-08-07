## Done report

EPIC T-0330's error-handling family (T-0623): fallibility-discipline
checks written once against the T-0609 normalized model, mirroring
T-0622's just-landed `_logging_checks.py` sibling.

`src/frob/arch/_fallibility.py` adds four ARCH1xx categories:
`unhandled-result` (a call to a same-module Result-returning function
whose line is not itself a `return` line -- explicitly disclosed as a
best-effort proxy, since `NormalizedCall` has no assignment/discard
field on the T-0609 model, so a genuine `x = foo()` local assignment
looks identical to a discarded bare-statement call under this model),
`swallowed-exception` (a bare/`Exception` catch with no raise/log-call/
return within a 3-line adjacency window), `recoverable-error-wrong-
signature` (a function raises `ValueError`/`KeyError`/`LookupError`/
`TypeError` but its declared return type is not `Result[...]`), and
`over-broad-except` (folding both "catches more than nameable" and
"re-raise-losing-context" into one category, per the ticket's own body
text presenting them as a single bullet).

`_models.py`'s scope lease was free at implementation time (same as
T-0622's) -- all four categories extend the shared `ArchCategory`/
`ArchSuggestion` directly, no local literal needed.

Per this dispatch's own instruction, `run_fallibility_checks` is defined
but not yet wired into `analyze_project`/the check pipeline -- T-0626
(last in this dispatch's queue) does the unified ARCH1xx registration.

### Verification
- `uv run pytest tests/unit/test_arch.py -p no:cacheprovider -q` -- full
  file, 203 passed (10 new: TestUnhandledResult x2,
  TestSwallowedException x2, TestRecoverableErrorWrongSignature x2,
  TestOverBroadExcept x3, TestRunFallibilityChecks x1).
- `uv run frob check --only lint --ticket T-0623` -- 0 errors, 0 warnings.
- `uv run frob check --only gates-fast --ticket T-0623` -- 0 errors
  (fixed the same INV006 module-docstring-prose hit T-0622 hit, via the
  same disclosed `frob:waive INV006` pattern, and the same PRE001
  staleness hit via `frob ticket sweep T-0623`).
- `uv run frob check --only gates-native --ticket T-0623` -- 0 errors.
- `uv run frob check --only gates-security --ticket T-0623` -- 0 errors.
- `git diff main --diff-filter=D --stat` -- empty.

### Cuts disclosed
- No wiring into `analyze_project`/the check pipeline (by design, per
  T-0626's own job).
- `unhandled-result`'s false-positive shape (assigned-but-unused local
  variables look identical to genuinely-discarded bare-statement calls)
  is a real model limitation, disclosed in both the module docstring and
  docs/modules/arch.md, not silently narrowed away.
- `over-broad-except`'s re-raise-losing-context signal cannot confirm a
  `raise ... from e` chain was actually omitted (no `from`-clause field
  on `NormalizedRaise`) -- same disclosed adjacency-proxy limitation
  every check in this module already carries.

### Changed
```
 docs/modules/arch.md             | 144 +++++++++++++
 src/frob/arch/_fallibility.py    | 399 ++++++++++++++++++++++++++++++++++
 src/frob/arch/_logging_checks.py | 335 ++++++++++++++++++++++++++++
 src/frob/arch/_models.py         |  21 ++
 tests/unit/test_arch.py          | 456 +++++++++++++++++++++++++++++++++++++++
 tickets.md                       | 116 +++++++++-
 6 files changed, 1465 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestUnhandledResult::test_bare_statement_call_to_result_function_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestUnhandledResult::test_returned_call_to_result_function_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSwallowedException::test_bare_except_with_no_reaction_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSwallowedException::test_except_with_nearby_log_call_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRecoverableErrorWrongSignature::test_raises_value_error_without_result_signature_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRecoverableErrorWrongSignature::test_raises_value_error_with_result_signature_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestOverBroadExcept::test_bare_except_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestOverBroadExcept::test_specific_except_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestOverBroadExcept::test_reraise_with_different_type_loses_context_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRunFallibilityChecks::test_combines_all_four_checks` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
