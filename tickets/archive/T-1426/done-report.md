## Done report

coverage combine without --append erases the base .coverage file before merging, via CoverageData._start_using's first-touch erase. pytest-cov's own DistMaster.finish already combines every xdist worker's data into that base file in-process before pytest exits, so the recipe's separate bare combine discarded the complete result and kept only stray satellite files.

Measured in isolation against real coverage.py 7.14.1 and the recipe's own subprocess rc shape: src/frob/__main__.py at 136 covered lines pre-combine, 0 after bare combine, 136 after combine --append.

This is the mechanism behind the TEST005 deflation that made all 306 zero-coverage findings artifacts (T-1418 classified them: zero genuine gaps, 289 of 306 covered by ordinary in-process unit tests, which ruled out the process-boundary theory). It is distinct from T-1353's worker-crash class and from T-1395's attribution hypothesis, and T-1353's own regression test could not have caught it -- that test exercises coverage run --append and never reaches the combine CLI action's erase gate at all.

The coverage-fast recipe's fallback to bare combine carried the identical hazard and was removed rather than left as a latent recurrence path.

DECLARED WAIVE DELETIONS, in the terms land's OutOfScopeWaiveDeletion guard asks for.

This branch merged main forward, which carried in two waivers added on main in commit 8fdb13bd while clearing main's last four errors. They are declared here because land's pre-merge pass surfaces them against this branch:

- src/frob/tickets/_accept.py : INV006 -- incidental exclusivity vocabulary, one occurrence inside another waiver's own reason text and one in a user-facing error message reporting how many criteria a ticket declares.
- tests/unit/test_ticket_close_bug002_t1427.py : OPAQUE001 -- pytest monkeypatch setattr calls over statically-written literal targets, the two genuine external boundaries BUG002 crosses plus its TEST016 sibling guard.

Neither belongs to this ticket's own work; both are unchanged by it. Naming them here per the guard's instruction rather than widening this ticket's scope to files it does not touch.

### Changed
```
 Makefile                                     |  23 +++-
 design/frob.strata                           |   1 +
 src/frob/tickets/_accept.py                  |  12 +-
 tests/unit/test_makefile_coverage.py         | 189 ++++++++++++++++++++++++++-
 tests/unit/test_ticket_close_bug002_t1427.py |  12 +-
 tickets.md                                   |  60 ++++++++-
 6 files changed, 279 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/unit/test_makefile_coverage.py::TestCombineAppendPreservesBaseData::test_combine_without_append_erases_base_data` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCombineAppendPreservesBaseData::test_combine_with_append_preserves_base_data` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 331 warning(s), 695 waived
- error-findings: PRE001@tickets/T-1426
