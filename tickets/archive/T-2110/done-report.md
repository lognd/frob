## Done report

### Changed
src/frob/__init__.py (added GlobalBinarySkew, global_binary_skew, commit_diff, recent_commits)
src/frob/serve/__init__.py (added frob_map)
src/frob/serve/_tools.py::__all__ (added frob_map)

### Evidence
tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols

Full test_exports.py re-verified: 16 passed. Targeted regression checks:
tests/test_doctor.py's 3 global_binary_skew tests: 3 passed.
tests/test_gitio.py::TestCommitDiff/TestRecentCommits: 4 passed.
(Full test_doctor.py/test_gitio.py runs timed out under session
contention -- collection succeeded cleanly, 13/many node ids
enumerated; targeted runs of the specifically-relevant tests are the
evidence recorded here, per playbook's own scoped-verification
guidance.)

### Investigation and verdict (judged individually, not blanket-added)

`GlobalBinarySkew`/`global_binary_skew`: clean, unambiguous gap.
`DoctorReport` (already exported) has a field for every OTHER
diagnostic/status type it composes (`NativeExtensionStatus`,
`DerivedArtifactStatus`, `MalformedTicketEdge`, `VenvShimDrift`,
`LiveLandProcess`), and every one of those is already in `frob.
__init__`'s `__all__` -- `GlobalBinarySkew` (the `global_binary` field's
type, T-1719) is the one exception. `global_binary_skew` is its
producer function, matching every sibling diagnostic's own exported
producer.

`commit_diff`/`recent_commits`: judged this pair the hardest. Measured
usage first (`git grep`, not assumption): exactly one production call
site (`src/frob/verify/_attribution.py`), narrower than the curation
rationale `frob/__init__.py`'s own module docstring states for its
existing `gitio` re-exports ("used across nearly every sub-package").
Initially leaned toward leaving these un-exported as a documented
exception. Reversed after reading `TestFrobExportsPolicyResidue`'s own
docstring, which commits this test to exactly two resolutions --
"a deliberate export ... or a demotion to private ... never a blanket
waiver" -- with no third "leave it, document why" option. Both symbols
have their own DIRECT, committed public unit tests
(`tests/test_gitio.py::TestCommitDiff`/`TestRecentCommits`, T-2018)
importing them as `frob.gitio` public API; demoting to private would
break that real, intentional test surface. Given the binary
constraint and that the alternative resolution is actively harmful,
exported both.

`serve._tools.frob_map`: clean, unambiguous omission. Registered in
`_socketd.py`'s real tool-dispatch table
(`"frob_map": _tools.frob_map`) exactly like every already-exported
sibling `frob_*` tool (`frob_affects`, `frob_check_delta`, etc.) --
same naming shape, same dispatch wiring. The gap existed at TWO levels
(`_tools.py`'s own `__all__`, and `serve/__init__.py`'s re-export of
`_tools`'s symbols) -- both fixed; the second was only discovered
after fixing the first and re-running the test, which still failed
against the `src/frob/serve` package specifically (disclosed as found
mid-fix, not planned from the start).

### Gates
`frob ticket evidence --check-repro`/`--designate-repro` against the
pre-fix commit (`fac9b7d49450ee2c90799a71356ac8fb57a75ad8`): genuine
FAILED_AT_PARENT.

Filed: none.

### Changed
```
 src/frob/__init__.py       |  8 ++++++++
 src/frob/serve/__init__.py |  2 ++
 src/frob/serve/_tools.py   |  1 +
 tickets/T-2110/ticket.md   | 11 ++++++++---
 4 files changed, 19 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: PRE001@tickets/T-2110
