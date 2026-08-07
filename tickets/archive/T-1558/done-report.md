## Done report

WIRE001's reachability scan (`_is_reached_outside_diff_tests`) skipped
EVERY test path unconditionally, on the correct theory that a production
symbol with only test callers is still dead in shipped code. That same
rule wrongly treated a symbol DEFINED under `tests/` the same way: a
shared test-fixture helper called from a DIFFERENT test file
(`tests/_cache_transparency.py::git_init`, called from
`tests/test_cache_transparency.py`) is genuinely wired -- just entirely
within the test tree -- but read as permanently unreachable, forcing a
waiver with nowhere real to point (16 instances accumulated against this
ticket as their open "waiver home" before this landed).

Fix: `_wire_test_path_excluded` (src/frob/gates/_wire.py) makes the
exclusion rule symbol-aware -- a production symbol still excludes every
test path (unchanged behavior); a test-tree-defined symbol excludes only
its OWN defining file, so a call from any OTHER test file now counts as
"reached". Extracted into its own function (rather than inlined into
`_is_reached_outside_diff_tests`) to keep that function under ARCH001's
line threshold and to give the rule its own documented, testable home.

Swept the 16 waivers this ticket was the open follow-up for:
- 3 genuinely cross-test-file cases (`tests/_cache_transparency.py::
  git_init`/`git_commit_all`/`run_cold_warm_sweep`) had their WIRE001
  waiver DELETED outright -- the gate no longer fires on them at all.
- 13 same-file-only private helpers (test_tickets_migration.py x6,
  test_cache_gate.py, test_cache_transparency.py, test_hotpath_smells.py,
  test_coverage_attribution_lock_t1395.py, test_serial_pools_import_
  failure.py x2, test_ticket_land.py) are genuinely unwired by design
  (same-file test-fixture builders, matching T-1592's precedent exactly)
  -- rebound from `follow_up="T-1558"` onto `permanent="true"` (T-1592's
  mechanism), landed on this ticket rather than staying an open waiver
  home with nothing left bound to it.

docs/modules/gates.md's WIRE001/WIRE002 section documents the new
cross-test-file rule and its same-file exception.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 1183 warning(s), 715 waived
- error-findings: none (measured, zero errors)
