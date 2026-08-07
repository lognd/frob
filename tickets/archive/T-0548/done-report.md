## Done report

docs/audits/gates-accounting.md B1/E1: TEST001, the only BLOCKING per-symbol
test gate, is satisfied by a single collected pytest node id whose name
contains the function's snake name -- nothing inspects assertions or
whether the symbol is even called. `def test_myfunc(): pass` clears it
today; TEST002 (case count) and TEST005 (branch coverage) are WARN-only,
so nothing blocks a repo of vacuous tests.

The ticket's own body correctly scoped the RIGHT-WAY fix as large and
cross-cutting: tying TEST001 credit to nonzero per-symbol branch coverage
(or promoting TEST005 to ERROR) touches TEST002/003/004/005/009's
severities and interactions together, plus the legacy-adoption WARN
campaign frob.toml documents -- "needs its own dedicated ticket" per the
original ticket body.

Landed (sound, zero-regression, matching TEST013/TEST014's restraint this
same audit pass): TEST015 (WARN). Rather than inventing new detection
logic, it reuses T-0549's existing, already-proven `_has_assertion_evidence`
heuristic -- previously only used to cap PARAMETRIZE-inflated case counts
back to 1 -- extended to the exact B1 shape: a public symbol whose TEST001
credit (via explicit edge OR the naming-convention fallback) comes ONLY
from test(s) with no assertion-shaped construct at all. Fires WARN naming
the symbol and an example vacuous test id; does not change what TEST001
itself blocks on.

Split off (the real fix + judgment call): T-draft-934c675a ("Tie TEST001
credit to real per-symbol coverage (promote TEST005/TEST015,
cross-cutting)") -- wiring `CoverageData` into `_test001_002` (which today
only sees `CollectedTests`, no coverage), deciding whether to require
`symbol_branch[record.symref] > 0` for TEST001 credit, and running the
same compat-survey discipline this audit pass used for T-0547/T-0556
before promoting anything.

Also noted (not touched): the T-draft-9557a879 COV002 grace-window
anomaly (found during T-0556) is still present against the base commit
`frob check` was run from here -- reproduces on symbols from prior closed
tickets, unrelated to T-0548's own new code (verified: all TEST015-related
new symbols in gates/__init__.py and test_gates.py are clean of COV002).

### Changed
```
 CHANGELOG.md                |  19 ++
 frob.lock                   |   2 +-
 pyproject.toml              |   2 +-
 src/frob/gates/__init__.py  | 253 ++++++++++++++++++++++++-
 src/frob/gates/_coverage.py | 125 +++++++++++-
 src/frob/graph/lock.py      |  27 ++-
 tests/test_gates.py         | 249 +++++++++++++++++++++++-
 tests/test_graph_lock.py    |  41 +++-
 tickets.md                  | 449 ++++++++++++++++++++++++++++++++++++++++++--
 uv.lock                     |   2 +-
 10 files changed, 1136 insertions(+), 33 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTest015VacuousCredit::test_fires_on_no_op_test_body` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTest015VacuousCredit::test_silent_when_any_matching_test_asserts` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTest015VacuousCredit::test_silent_when_no_test_matches_at_all` (pytest node id, verified passing when recorded)
