## Done report

The T-1514 pre-commit unscoped sweep compared staged-tree findings against the pre-land baseline with no allowance for the files the land machinery itself rewrites at that checkpoint. A land needing a REL001 version bump stages .frob-release.json/CHANGELOG.md/pyproject.toml changes; PRE001/SCOPE001 then fired against them as new-vs-baseline and refused the land (observed blocking T-1517 twice on 2026-08-04, while non-bumping lands passed). Fix: _LAND_OWNED_SWEEP_EXEMPT + _is_land_owned_finding filter exclusions from both the initial comparison and the post-Tier-A re-check, logged loudly per the no-silent-caps rule; matching is restricted to repo-root paths so a nested pyproject.toml in a fixture tree still refuses. Two unit tests cover the exemption and the nested-name boundary.

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py   | 66 +++++++++++++++++++++++++++
 tests/test_ticket_work_and_land_finish.py | 74 +++++++++++++++++++++++++++++++
 tickets.md                                | 50 ++++++++++++++++++++-
 3 files changed, 189 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn::test_land_owned_only_findings_are_exempt_and_pass` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn::test_nested_land_owned_name_is_not_exempt` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
