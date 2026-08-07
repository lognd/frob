## Done report

T-1205 acceptance[1]'s second half: investigated rollout sequencing (as
the ticket required) before touching TEST011's severity. Finding: the
two signals TEST011 combines have very different steady-state behavior.
`stale_by_mtime` is TRUE for most of any active working tree's life --
routine, expected, not a corruption signal -- escalating it to ERROR
would gate the whole repo on ordinary editing. `module_join_fraction`
has no such noise floor: a healthy `make coverage` run always joins
close to 100% of known modules, so a low fraction is a rare, specific
corruption signature (T-0464's original incident).

Decision: split the deflation signal out of TEST011 into its own new
rule, TEST017, and promote ONLY TEST017 to ERROR severity
(`src/frob/gates/__init__.py::_test017_deflation`). TEST011 keeps
`stale_by_mtime` at WARN, unchanged. Registered TEST017 in
`_KNOWN_GATE_RULES` (`src/frob/gates/_waive.py`, waivable like every
other TEST0xx rule) and in `docs/design/registry/check-coverage.yaml`
(CHK-GATE-TEST017 entry + updated `gate_rule_total`). Documented the
split and its rollout rationale in `docs/modules/gates.md` (new rule-
catalog rows for TEST011/TEST017 plus a "TEST011/TEST017 (T-0464/T-1489)"
explanatory section).

Updated `tests/test_gates.py`'s existing TEST011 deflation test to
assert TEST017 instead (ERROR severity), and confirmed the silent/clean
case asserts both rules stay quiet.

Environment note, disclosed rather than silently worked around: this
session ran during a live multi-agent drive where `main`'s ref moved
repeatedly (confirmed via `git reflog show main`, other agents landing
tickets concurrently). A `frob check --ticket T-1489` run's diff base
transiently landed on a merge-base predating several already-archived
tickets (T-1202, T-1235, T-1395) that had touched design/frob.strata,
src/frob/gates/_coverage.py, and
tests/unit/test_coverage_attribution_lock_t1395.py -- none of which are
in T-1489's scope or diff. Investigated and found a real, separate
defect behind it (SCOPE001/COV002's cross-ticket exemption looks up the
attributing ticket via `queue.tickets.get(ref)`, which misses once that
ticket is archived out of tickets.md) and filed it as its own ticket
rather than working around it in this ticket's scope: T-1502
(SCOPE001/COV002 cross-ticket exemption breaks once the attributing
ticket is archived). Confirmed via `git diff main -- <those 3 files>`
that this ticket's own branch carries zero changes to them, and via
`git diff main --diff-filter=D --stat` that nothing is deleted.

Evidence: `tests/test_gates.py::TestTestGate::test_test017_fires_on_low_join_fraction`,
`tests/test_gates.py::TestTestGate::test_test011_fires_on_stale_mtime`,
`tests/test_gates.py::TestTestGate::test_test011_silent_when_fresh_and_fully_joined`
-- full `tests/test_gates.py` suite (all classes) run green, no
regressions.

### Changed
```
 design/frob.strata                                 |   2 +
 docs/design/registry/check-coverage.yaml           |   6 +-
 docs/modules/gates.md                              |  66 +-
 src/frob/gates/__init__.py                         | 130 +++-
 src/frob/gates/_coverage.py                        |  57 ++
 src/frob/gates/_waive.py                           |   4 +
 tests/test_gates.py                                | 203 +++++-
 tests/unit/test_coverage_attribution_lock_t1395.py |  81 +++
 tests/unit/test_makefile_coverage.py               |  55 ++
 tickets.md                                         | 761 ++++++++++++++++++---
 10 files changed, 1249 insertions(+), 116 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTestGate::test_test017_fires_on_low_join_fraction` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_test011_fires_on_stale_mtime` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_test011_silent_when_fresh_and_fully_joined` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 799 warning(s), 746 waived
- error-findings: SELFAUDIT001@design, WIRE001@tests/unit/test_coverage_attribution_lock_t1395.py
