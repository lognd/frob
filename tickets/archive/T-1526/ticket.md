---
id: T-1526
title: 'coverage: make make coverage/coverage-fast a thin wrapper over native_coverage_refresh'
state: done
kind: feature
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- Makefile
- tests/unit/test_makefile_coverage.py
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: rewriting coverage-fast into a thin wrapper obsoletes tests/unit/test_makefile_coverage.py's
    own recipe-content assertions about the old inline xargs/rc logic; must update
    them in the same change, and testing.md documents the make-target contract
  actor: logan
  at: '2026-08-05'
- op: add
  glob: docs/modules/testing.md
  reason: rewriting coverage-fast into a thin wrapper obsoletes tests/unit/test_makefile_coverage.py's
    own recipe-content assertions about the old inline xargs/rc logic; must update
    them in the same change, and testing.md documents the make-target contract
  actor: logan
  at: '2026-08-05'
evidence:
- tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc
- tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_still_rebuilds_natives_first
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_coverage_xml_invocations_pass_ignore_errors
  new_node: tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests. Shared
    claim: the coverage-xml step always passes -i/--ignore-errors. Successor exercises
    native_coverage_refresh''s own ''coverage xml -i'' call directly (coverage-fast
    now delegates entirely to native_coverage_refresh per this same ticket''s own
    T-1526 rewrite, so there is no separate Makefile-side xml invocation left to test).'
  actor: logan
  at: '2026-08-17'
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1205 acceptance[3] asks for make coverage to become a thin optional wrapper around the frob-native orchestration. T-1516 added native_coverage_refresh and rewired run_coverage_wait's default onto it, but the Makefile coverage/coverage-fast targets themselves were left untouched (they still run the full ~300-line shell recipe independently). Rewrite them to delegate their common-path work to native_coverage_refresh, keeping only the xdist-crash-recovery/rerun-deadline shell logic (or whatever that becomes once T-1524 lands) as the part that stays Makefile-side, or is itself ported.

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
