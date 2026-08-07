## Done report

Rewrote `coverage-fast:` (Makefile) into a thin wrapper: `$(MAKE) core &&
uv run frob doctor || exit 1` (unchanged natives-clobber guard, T-0538)
followed by a single `uv run frob coverage .` call -- the ~15-line inline
`xargs uv run pytest --cov-append`/`coverage combine`/`coverage xml -i`/
`frob check --stamp-coverage` sequence is gone; `frob coverage` (T-1525)
now performs that exact sequence via `native_coverage_refresh` (T-1516)
in-process, cross-platform, no Makefile/shell dependency for the common
path.

`coverage:` (the full-suite target) is intentionally UNCHANGED -- this
ticket's own acceptance text keeps "the xdist-crash-recovery/rerun-
deadline shell logic ... Makefile-side", and `coverage-fast:` had no such
resilience of its own to begin with (it was already re-deriving exactly
what `native_coverage_refresh` now does as a library call, per T-1516's
Done report) -- `coverage:` is the one that legitimately needs to keep
its shell recipe.

Known limitation, disclosed rather than silently regressed: the old
`coverage-fast:` respected `BASE ?= main` (`make coverage-fast
BASE=<ref>` overrode the touched-set diff base). `frob coverage` has no
`--base` flag today -- `native_coverage_refresh`'s own default is `base=
"HEAD"`, not `main`. `frob coverage`'s CLI scope (T-1525) did not extend
to adding a `--base` override; filed a follow-up ticket (draft
T-1572 at filing time -- renumbers to a real id at land, see
tickets.md) to add one and wire it through `coverage-fast: BASE=$(BASE)
uv run frob coverage . --base $(BASE)` once it exists. Until then, `make
coverage-fast BASE=<ref>` no
longer honors a non-default `BASE` -- worth flagging to anyone who used
that override, though the common case (default `main`) already differs
from HEAD in ways that usually select a similar or larger touched set,
not a smaller one, so this is unlikely to under-select tests silently.

tests/unit/test_makefile_coverage.py updated in the same change (added to
scope via `frob ticket scope --add --reason`, alongside
docs/modules/testing.md): `TestCoverageFastUsesAbsoluteSubprocessRc`'s
three methods (T-1397's own evidence bindings) were REWORDED, not
deleted or renamed -- same method names, updated bodies asserting the
stronger post-rewrite invariant (no inline `COVERAGE_PROCESS_START`/
`xargs`/`pytest` left in `coverage-fast:` at all, so the whole class of
bug T-1397 exists to prevent is now structurally impossible, not merely
avoided) -- this keeps T-1397's already-`done`/archived evidence
resolving instead of orphaning it (COV003 caught the dangling-evidence
shape on the first check pass when these methods were initially replaced
outright; fixed by reusing the names). `TestCoverageXmlIgnoreErrors.
test_coverage_xml_invocations_pass_ignore_errors`'s expected `uv run
coverage xml` call count dropped from 2 to 1 (coverage-fast's own call is
gone, replaced by `native_coverage_refresh`'s in-process `coverage xml
-i` subprocess call, not Makefile shell text).

docs/modules/testing.md: fixed pre-existing drift in
`run_coverage_wait`'s documented signature (still showed the pre-T-1516
`command: tuple[str, ...] = ("make", "coverage-fast")` default instead of
the real `tuple[str, ...] | None = None`), and updated
`native_coverage_refresh`'s docstring block to note `coverage-fast` no
longer has xdist-crash-recovery of its own to lose (it never had any).

src/frob/__main__.py: one edge-comment addition
(`# frob:ticket T-1525` above `_add_workflow_subparsers`) -- COV002
flagged the function (already changed by T-1525's own diff, committed
before T-1526 started) with no `frob:ticket` edge; added under this
ticket's own gate-fix pass since it blocked `--ticket T-1526`'s check
run, not a scope violation (T-1525's own scope already covers
`__main__.py`, and T-1525 is still in-progress, not closed).

Targeted tests: `tests/unit/test_makefile_coverage.py` -- 21 passed
(includes T-1397's rebound evidence). `frob check --ticket T-1526`: no
ERROR-level finding traces to a file this ticket touched. `frob check
--land-parity`: clean, 0 unscoped errors.

### Changed
```
 README.md                          |   3 +-
 docs/modules/cli.md                |  41 +++++++
 src/frob/__main__.py               |   2 +
 src/frob/_cli_parsers/__init__.py  |   2 +
 src/frob/_cli_parsers/_misc.py     |  28 +++++
 src/frob/app/_config_external.py   |   4 +
 src/frob/app/app.py                |   4 +
 src/frob/app/config.py             |  11 ++
 src/frob/app/coverage_runner.py    |  84 ++++++++++++++
 tests/unit/test_coverage_runner.py |  78 +++++++++++++
 tickets.md                         | 232 ++++++++++++++++++++++++++++++++++++-
 11 files changed, 485 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_still_rebuilds_natives_first` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_coverage_xml_invocations_pass_ignore_errors` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 357 warning(s), 782 waived
- error-findings: none (measured, zero errors)
