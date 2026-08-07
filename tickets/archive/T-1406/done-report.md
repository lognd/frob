## Done report

Fixed module_join_fraction's denominator to scope against the coverage.xml
run's own declared --cov roots instead of every .py file in the repo.

load_coverage already computes candidate roots for the (pre-existing)
class-filename join heuristic via _parse_sources/_repo_relative_root; this
reuses that same machinery to compute declared_roots once more and filter
_known_repo_paths's unscoped result through a new helper,
_scope_known_paths_to_coverage_roots, before handing it to
_module_join_fraction and _unjoined_python_modules. _known_repo_paths
itself is left unscoped and still feeds _parse_classes as before -- that
call genuinely needs the full repo-wide set to disambiguate which --cov
root a given <class filename=...> resolves under (T-0311); only the
join-fraction DENOMINATOR (a different question -- "how much of what this
run could ever measure did it measure") narrows.

Verified the real-incident shape directly: a src/frob/pkg/a.py file fully
covered plus a tests/test_a.py file outside the declared src/frob root now
reports module_join_fraction == 1.0 (previously 0.5, since tests/test_a.py
counted against the denominator despite --cov=src/frob structurally never
being able to report on it). Confirmed the no-<sources>-to-scope-against
fallback (empty declared_roots, or every entry unresolvable against the
checkout) leaves known_paths unchanged, preserving the pre-T-1406 floor
behavior in that degraded case rather than dividing by nothing.

Updated _DEFLATION_FLOOR's own comment and
_scope_known_paths_to_coverage_roots's docstring to document both the new
scoping and the documented fallback explicitly, satisfying this ticket's
acceptance criterion 1 either way -- the scoping now exists AND both paths
(scoped, and the unscoped fallback) are documented at the constant itself.

### Changed
```
 src/frob/app/check_runner.py          |  54 +++++++++
 tests/test_gates.py                   |  32 +++++
 tests/unit/test_app_runners_batch6.py | 125 +++++++++++++++++++-
 tickets.md                            | 214 ++++++++++++++++++++++++++++++++--
 4 files changed, 412 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageLoad::test_module_join_fraction_excludes_files_outside_declared_cov_root` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageLoad::test_scope_known_paths_no_declared_roots_falls_back_unchanged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 3 error(s), 861 warning(s), 695 waived
- error-findings: DUP001@src/frob/gates/_coverage.py, PRE001@tickets/T-1406, WIRE001@tests/unit/test_app_runners_batch6.py
