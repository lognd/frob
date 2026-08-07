## Done report

Added `# frob:waive PERF004 reason="sorts each pair's own 2-tuple; data
differs per iteration, O(1), cannot be hoisted"` at tests/test_dup_prefilter.py:52.
This is a genuine false-positive of the indentation-blind PERF004 heuristic
(the systematic detector fix is tracked in T-0367). Verified: `uv run frob
check --only perf` now reports 0 unwaived PERF004. This was the last
non-waived warning in the blocking `gates` stage.
