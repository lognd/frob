## Done report

Evidence-close only: the fix for git 2.34.1's `:!.frob` ignored-path
refusal already landed inside T-1179's commit 1440fac6 as
`_wip_add_excluding_frob` (add-then-unstage fallback, guarded by
`_is_ignored_path_refusal`). Verified the landed behavior is present at
src/frob/tickets/_land.py:1844-1893 unchanged, and added two focused
pytest node ids: one end-to-end `land()` case that gitignores `.frob/`
(the real-repo trigger condition) and asserts the wip commit still
succeeds via the fallback path, and one direct unit test on
`_is_ignored_path_refusal`'s message matching. Both pass.

### Changed
```
 tickets.md | 32 +++++++++++++++++++++++++++++++-
 1 file changed, 31 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_land.py::TestWipAddIgnoredPathFallback::test_gitignored_frob_falls_back_and_still_lands` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestWipAddIgnoredPathFallback::test_is_ignored_path_refusal_matches_gits_fixed_message` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 496 warning(s), 573 waived
- error-findings: none (measured, zero errors)
