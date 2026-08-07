## Done report

T-0582 re-measured docs/audits/perf.md's H4/H5 findings and profiled the
refs stage for the first time. H4 (vet's scan_file_capabilities bypassing
the T-0410 parse memo) is RESOLVED -- not by T-0410 itself but by T-0414
(a later, more general fix that memoizes frob.lang._parse directly, which
raw_tree/scan_file_capabilities inherit for free): confirmed via a direct
parse_cache_stats measurement across all 592 tracked .py files (1776
hits/592 misses, zero redundant parses), bound as evidence via the
existing T-0414 anti-regression test. H5 (selfconform's double
capability-scan) is STILL UNFIXED; its cost shape changed (double
resolution-pass, not double-parse) but is real. The refs stage (10.5-13.5s
CPU, 2nd dominator behind test) was profiled and root-caused for the first
time: an O(files^2 x tokens_per_file) pairwise token-reach scan in
_auto_inbound/_tokens_reach (src/frob/gates/_refs.py). A new finding not
in the original audit also surfaced: once parsing is cheap, vet's own
capability-resolution work (_python_binding_capabilities' per-candidate
needle sweep) is itself a real ~23s/592-files algorithmic cost, distinct
from any caching gap.

All three actionable findings outside T-0582's scope (src/frob/vet/,
docs/audits/perf.md) were filed as follow-up tickets rather than fixed
blind: refs O(n^2) scan, selfconform H5 merge, and a vet capability-scan
algorithmic investigation. The full measurement table and verdicts are
recorded in docs/audits/perf.md's new dated section.

### Changed
(no changed files detected)

### Evidence
- `tests/test_lang.py::TestParseCache::test_cross_entry_point_reuse_is_one_parse_per_file` (pytest node id, verified passing when recorded)
