## Done report

Fully absorbed by T-0975's already-landed fix, present on main before
this ticket was started: test_stamp_baseline_only_chunk_records_without_
stamping (tests/unit/test_app_runners_batch6.py) no longer hardcodes the
gates-native gate-name literal set -- it derives the expected set from
frob.check._STAGE_GROUPS["gates-native"], the live stage-group registry,
exactly the same "derive from the live registry, not a literal" pattern
this ticket asked for, per the ticket's own T-0975 precedent pointer.
Re-ran the test fresh against main with T-0894/T-0900/T-0898 merged in;
it passes. No hardcoded frozenset with archgate/clones/perf literals
remains anywhere in this file. No new code or test needed -- closing
citing the pre-existing T-0975 evidence.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_records_without_stamping` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 2618 warning(s), 339 waived
- error-findings: none (measured, zero errors)
