---
id: T-1362
title: Fix ty no-matching-overload regression in test_makefile_coverage.py (T-1335
  follow-up)
state: done
kind: bug
origin: human
created: '2026-07-31'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/unit/test_makefile_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_combine_then_xml_survives_a_stale_fixture_path
  new_node: tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests. Shared
    claim: the coverage.xml step is always invoked with -i/--ignore-errors so a torn-down/stale
    source path does not abort the run (T-1320). native_coverage_refresh''s coverage-xml
    call unconditionally passes ''coverage xml -i'' per its own T-1320 comment, exercised
    end to end by this node.'
  actor: logan
  at: '2026-08-17'
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1335's own new regression test (tests/unit/test_makefile_coverage.py)
introduced 2 new `ty` no-matching-overload errors: it builds a plain
dict of subprocess.run kwargs and unpacks it with **run_kwargs across two
call sites, which ty's overload resolution cannot match against
subprocess.run's typeshed overloads (an untyped dict loses the literal
`text=True`/`check=True` types the overloads key on). Found immediately
after T-1335 landed, while verifying T-1351's --ticket lint stage
(`frob check --ticket T-1351 --only lint`) showed 3 ty diagnostics where
the prior full run showed only 1 (src/frob/gates/_debt_deprecated.py,
pre-existing, unrelated).

Fix: pass the subprocess.run kwargs directly at each call site instead of
via a dict-unpack, so ty can resolve the real overload from literal
keyword arguments.

## Done report

Fixed both new `ty` no-matching-overload errors introduced by T-1335's
test_makefile_coverage.py: the two subprocess.run calls that previously
unpacked a plain dict (`**run_kwargs`) now pass their kwargs as literals
at each call site, so ty can resolve the real subprocess.run overload
from the literal text=True/check=True arguments instead of losing that
information through an untyped dict.

Verified: `uv run ty check tests/unit/test_makefile_coverage.py` -> "All
checks passed!" (previously 2 diagnostics here); the full repo `ty check`
is back down to its pre-existing 1 diagnostic (src/frob/gates/
_debt_deprecated.py, unrelated, predates this ticket). All 4 tests in
tests/unit/test_makefile_coverage.py still pass unchanged.

### Changed
```
 tickets.md | 62 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++---
 1 file changed, 59 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_combine_then_xml_survives_a_stale_fixture_path` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 5 error(s), 862 warning(s), 687 waived
- error-findings: INV006@src/frob/app/__init__.py, INV006@src/frob/app/app.py, PRE001@tickets/T-1362, SELFAUDIT001@design, TICK003@tickets.md
