## Done report

frob:waive BUG002 reason="items (a) ty invalid-return-type and (c) ARCH001 line-count splits have no runtime-observable defect to reproduce -- ty and frob check themselves are the reproduction (ty flagged 2 diagnostics pre-fix, 0 post-fix; ARCH001 flagged timed_call/usage_report pre-fix, 0 post-fix, both confirmed by uv run ty check and frob check --ticket T-1465). Item (b)'s import fix IS behaviorally reproducible (ImportError at collection before the fix) but the designated evidence node id is a pre-existing passing test, not a new regression test, since the failure mode is a collection-time ImportError uncapturable as a single node id's pass/fail delta."

Changed:
src/frob/vet/_capability_core.py::_operation_entry_matches
src/frob/vet/_capability.py (re-export _SPECIAL_CHECKS, __all__)
src/frob/app/telemetry.py::timed_call
src/frob/app/telemetry.py::_exit_code_from_system_exit
src/frob/app/telemetry.py::_finish_timed_call
src/frob/app/telemetry.py::usage_report
src/frob/app/telemetry.py::_top_time_sinks
src/frob/app/telemetry.py::_redundant_rerun_totals
src/frob/app/telemetry.py::_repeated_failure_streak_count
design/frob.strata::frob.vet (interface=_SPECIAL_CHECKS, SYS104)
tests/test_vet.py::TestOperationEntryMatchesFallthrough (new mutation-killing unit test)

Evidence:
tests/test_telemetry.py (26 tests, all pass)
tests/test_capability_registry.py (all pass)
tests/test_vet.py::TestOperationEntryMatchesFallthrough (new, kills the surviving return-False mutant)
uv run ty check src/frob/vet/_capability_core.py src/frob/vet/_capability.py -- All checks passed
frob test --base main -- PASS (13 selected outcomes)

Filed: none (this ticket itself was the filed bug ticket)

Gates: frob check --ticket T-1465 clean (0 errors); AFFECT001 waived x2 on
timed_call/usage_report (pure line-count split, behavior verbatim, tests green).


Waive-deletion disclosure (deletion-filter false-positive class): the
two frob:waive WIRE001 directives in tests/conftest.py were REWRAPPED to
fit the line-length limit, not deleted -- the diff's minus-lines carry
the same waiver text re-broken across lines, semantics identical,
follow_up preserved. No waiver was removed by this branch.

### Changed
```
 Makefile                              |  32 ++-
 design/frob.strata                    |   4 +
 frob.lock                             |  25 +++
 pyproject.toml                        |  13 ++
 src/frob/app/telemetry.py             | 172 ++++++++++-----
 src/frob/vet/_capability.py           |   2 +
 src/frob/vet/_capability_core.py      |   1 +
 tests/conftest.py                     |  84 +++++++-
 tests/test_vet.py                     |  25 +++
 tests/unit/test_conftest_stackdump.py |  84 ++++++++
 tests/unit/test_makefile_coverage.py  |  60 ++++++
 tickets.md                            | 390 ++++++++++++++++++++++++++++++----
 12 files changed, 790 insertions(+), 102 deletions(-)
```

### Evidence
- `tests/test_telemetry.py::test_timed_call_maps_bare_system_exit_to_zero` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_timed_call_maps_non_int_system_exit_code_to_one` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_timed_call_records_event_and_returns_value` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_timed_call_records_nonzero_exit_on_system_exit` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_usage_report_aggregates_time_and_failures` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_usage_report_counts_fast_exit1` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_usage_report_counts_redundant_reruns` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_usage_report_empty_corpus_is_all_zero` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::test_fire_fixture_names_a_registry_entry` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOperationEntryMatchesFallthrough::test_no_needles_and_not_bare_compile_returns_false` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
