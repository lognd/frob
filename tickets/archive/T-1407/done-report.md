## Done report

INVESTIGATION ticket -- the deliverable is a root-cause finding plus
follow-up tickets, not new production code of its own. Docs-only change
(docs/guides/agent-playbook.md); evidence is the existing CLI-dispatch
integration test per the T-0167 precedent (section 5), since there is no
pytest surface of this ticket's own to lock.

FINDING 1 (resolved this dispatch, by T-1406, same worktree/series):
the "~53% of known modules join even from a full make coverage run"
mystery is NOT a measurement/instrumentation gap. It is a denominator bug.
module_join_fraction's denominator (_known_repo_paths) counted every .py
file in the WHOLE repo -- tests/**, scripts, everything -- even though
make coverage runs pytest --cov=src/frob, which can structurally never
report coverage for anything outside that root. 447 real src/frob modules
/ 851 repo-wide known modules = 0.53 is arithmetic against the wrong
denominator, not evidence any run ever dropped real subprocess data. Fixed
in T-1406 (this same series): _scope_known_paths_to_coverage_roots scopes
the denominator to coverage.xml's own <sources> declaration before
dividing. This resolves T-1407's finding 1 in full -- confirmed by reading
the fix and its regression test directly (T-1406 is a sibling ticket in
this dispatch, not a hypothesis).

FINDING 2 (confirmed still open, no code fix in this ticket):
the claim that burn-down agents' own scoped verification runs leave a
stale/narrow coverage.xml on disk that a LATER unscoped frob check
misreads as full-run data remains unaddressed -- there is currently no
mechanism distinguishing "this coverage.xml is the full run" from "this is
a narrower scoped run left over on disk." T-1398's own investigation
(cited in this ticket) already independently ruled out a _coverage.py
join-code defect for the specific "exactly 0.0%" symptom three burn-down
agents reported; T-1407's own brief's proposed fix (a stamp-time
provenance check comparing a fresh coverage.xml's module count/join
fraction against the last committed lock's) is the right shape and is
filed as a follow-up rather than implemented here, since it needs T-1406's
denominator fix to have actually landed and been observed against a real
make coverage run before any threshold can be calibrated honestly.

Filed follow-up: see Filed below. Documented both findings in
docs/guides/agent-playbook.md section 6e so neither needs re-deriving from
scratch by a future investigation.

Disclosed cut: this ticket's own scope named src/frob/gates/_coverage.py
and Makefile in addition to the playbook doc. No Makefile change was
needed -- the recipe itself was never the defect, only the denominator
calculation _coverage.py itself performs on data the recipe already
produces correctly. No _coverage.py change in T-1407 itself either: the
fix for finding 1 already landed via the sibling T-1406 ticket in this
same dispatch, and finding 2's fix is the filed follow-up, not something
this investigation ticket implements directly.

### Changed
```
 src/frob/app/check_runner.py          |  54 +++++++
 src/frob/gates/_coverage.py           |  93 +++++++++++-
 tests/test_gates.py                   |  77 ++++++++++
 tests/unit/test_app_runners_batch6.py | 125 +++++++++++++++-
 tickets.md                            | 267 ++++++++++++++++++++++++++++++++--
 5 files changed, 600 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 3 error(s), 395 warning(s), 695 waived
- error-findings: DUP001@src/frob/gates/_coverage.py, PRE001@tickets/T-1407, WIRE001@tests/unit/test_app_runners_batch6.py
