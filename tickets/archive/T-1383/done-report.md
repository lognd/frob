## Done report

T-1381 closed leaving three obligations its own change created: `stamp` is
public and its contract changed (it can now refuse), so it needs a
`frob:doc` edge, and the guard's two new public test classes were
undeclared on the `testsuite` strata node (SYS104).

Added a docs/modules/release.md section explaining WHY stamping alone is a
footgun -- it rebaselines the recorded API at the current version, so the
gate goes green while the release never happens -- plus the two cases that
deliberately pass through (first-ever stamp, already-adequate version) and
the `--allow-unbumped` override. Pointed `stamp`'s `frob:doc` at it and
synced design/frob.strata.

This is the second time in a row (T-1380, now T-1383) that a ticket closed
before its own doc/strata/REL obligations were discharged, each time
needing a follow-through ticket. Worth folding into `frob ticket close` as
a pre-close check rather than discovering it on the next unscoped run --
that is the same systematize-the-footgun rule T-1381 itself came from.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_release_stamp_guard.py::TestStampRefusesUnbumped::test_refuses_when_api_changed_and_version_not_bumped` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 3 error(s), 1714 warning(s), 697 waived
- error-findings: E501@/home/logan/projects/frob/src/frob/tickets/_land.py:1231, F401@/home/logan/projects/frob/tests/unit/test_scope_lease_deadlock.py:25, F841@/home/logan/projects/frob/tests/unit/test_scope_lease_deadlock.py:215
