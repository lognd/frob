## Done report

All 3 residual COV006 findings from T-0528's calibration pass were
genuinely wrong bindings in the sense the ticket described (asserts a
module-level constant's set membership/equality, never calls the bound
private symbol) -- but retargeting the `frob:tests` directive straight at
the constant (the ticket's first suggested fix) does not work in
practice: tried it for all three, and `frob check`'s DRIFT002 then
reports the ref as unresolvable, because a bare module-level assignment
(`_FINGERPRINT_PACKAGES`, `SCANNED_LANGUAGES`, `_EXTENDED_KINDS`) is not a
graph node `frob ack` can bind against -- trading COV006 for DRIFT002.
Used the ticket's second suggested fix instead: `frob:waive COV006` with
the same module-constant-drift-lock reasoning T-0516's precedent
(tests/test_gates.py) already established, on each of the 3 tests, kept
the original (pre-existing, if slightly imprecise) `frob:tests` bindings
unchanged.

Verified `uv run frob check` (repo-wide, not just `--ticket`): `gate:COV
0 errors, 0 warnings, 75 waived` -- COV006 unwaived = 0 repo-wide, the
ticket's stated target.

### Changed
```
 Makefile                              |  29 +++++
 docs/modules/testing.md               |  11 ++
 src/frob/gates/__init__.py            | 110 ++++++++++++++++-
 tests/test_coverage.py                |  65 +++++++++-
 tests/test_gates_tick005.py           | 218 ++++++++++++++++++++++++++++++++++
 tests/test_graph.py                   |  11 ++
 tests/test_ticket_land.py             |  35 ++++++
 tests/unit/strata/test_selfconform.py |  18 +++
 tickets.md                            | 171 ++++++++++++++++++++++++--
 9 files changed, 656 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/test_graph.py::TestBuildIncremental::test_fingerprint_packages_derived_from_lang_registry` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestLanguageCoverageDriftLock::test_scanned_languages_equals_registry_languages` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map` (pytest node id, verified passing when recorded)
