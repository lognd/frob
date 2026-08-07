## Done report

Scope fix (T-1431 relocated-symbols class): src/frob/_cli_parsers.py was
split into a package (src/frob/_cli_parsers/: __init__.py, _check.py,
_core.py, _misc.py, _reporting.py, _ticket/) after this ticket was filed;
the single-file glob matched nothing. Narrowed scope to
src/frob/_cli_parsers/** (+ a placeholder test glob for any future
dedicated test file; tests/test_cli_parsers.py never existed).

Verification: copied the coordinator's authoritative green-suite
coverage.xml into the worktree (per dispatch instructions, not
regenerated) and ran frob check --only test --ticket T-1311. The full
gate:TEST output has zero TEST005/TEST003/TEST001 findings anywhere under
src/frob/_cli_parsers/**. Cross-checked coverage.xml directly: every
class under _cli_parsers/ reports branch-rate=1 and line-rate=1
(__init__.py, _check.py, _core.py, _misc.py, _reporting.py,
_ticket/__init__.py, _ticket/_closeout.py, _ticket/_metadata.py,
_ticket/_new.py, _ticket/_progress.py, _ticket/_query.py -- 11/11 files,
100% branch and line).

The ticket's original "6 findings" count predates the package split /
prior burn-down work elsewhere in the drive; against the current
authoritative coverage data there are 0 TEST005 findings left to fix.
No new tests were written -- there is nothing left to close, and adding a
test against an already-100%-covered symbol would be exactly the filler
the acceptance criteria warn against. No 0.0%-branch/dead-code symbols
were found in this package (ticket text already noted none exist).

Evidence: the existing CLI-dispatch integration coverage for this
package is exercised by tests/integration/test_interfaces.py's
test_main_cli_dispatches (per playbook section 5, docs-only/no-new-
surface precedent) plus the full existing test suite that already
produced the 100% coverage seen in coverage.xml.

### Changed
```
 tickets.md | 170 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 165 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 236 warning(s), 745 waived
- error-findings: none (measured, zero errors)
