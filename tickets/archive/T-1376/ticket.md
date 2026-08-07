---
id: T-1376
title: 'condition-coverage is never parsed: branch_pct is hit/not-hit, so TEST005
  measures the wrong thing'
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_coverage.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestConditionCoverageIsActuallyParsed::test_partial_condition_coverage_is_read_verbatim
- tests/test_gates.py::TestConditionCoverageIsActuallyParsed::test_three_way_partial_is_not_snapped_to_an_extreme
- tests/test_gates.py::TestConditionCoverageIsActuallyParsed::test_zero_and_full_condition_coverage_round_trip
designated_repro_test: null
acceptance:
- text: GIVEN a Cobertura line with condition-coverage='50% (1/2)' WHEN _parse_line_el
    runs THEN branch_pct is 50, not 100
  evidence:
  - tests/test_gates.py::TestConditionCoverageIsActuallyParsed::test_partial_condition_coverage_is_read_verbatim
  - tests/test_gates.py::TestConditionCoverageIsActuallyParsed::test_three_way_partial_is_not_snapped_to_an_extreme
- text: GIVEN the repo's own coverage.xml WHEN every branch line is parsed THEN the
    produced branch_pct values include partial percentages, not only 0 and 100
  evidence:
  - tests/test_gates.py::TestConditionCoverageIsActuallyParsed::test_zero_and_full_condition_coverage_round_trip
threat: null
component: null
---
Found 2026-08-01 while writing mutation-killing tests for T-1371's TEST016 survivors.

_parse_line_el computes branch_pct as int(cond_cov.split('(')[-1].split('%')[0].strip()). For the real Cobertura format '50% (1/2)', split('(')[-1] yields '1/2)', and split('%')[0] leaves it unchanged, so int() ALWAYS raises ValueError and the except branch silently falls back to '100 if hits > 0 else 0'.

The percentage is therefore NEVER read. Measured against this repo's own coverage.xml: the parser emits exactly two distinct values, 100 (1963 lines) and 0 (8063 lines), while 1324 branch lines carry a genuinely partial condition-coverage that is being rounded to one extreme or the other.

So symbol_branch is not branch coverage at all -- it is 'was this line hit'. Every TEST005 threshold, every entry in frob-coverage.lock.json, and the whole 1476-finding TEST005 backlog are computed from this. A half-covered branch on a hit line reads as 100%.

The fix is cond_cov.split('%')[0].strip(). Expect the corrected numbers to move DOWN for partially-covered code, which will surface TEST005 findings that were previously invisible -- the ratchet floors in frob-coverage.lock.json will need re-baselining against honest data, not clamped as a regression.

The except-branch fallback is correct and should stay for genuinely malformed input; T-1371 added tests pinning it.