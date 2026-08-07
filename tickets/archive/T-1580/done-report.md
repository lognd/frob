## Done report

<!-- frob:waive DOC006 reason="historical Done report describing the deletion of docs/modules/gates_e501_autofix.md itself, which by definition no longer exists after this ticket landed" -->
Folded `docs/modules/gates_e501_autofix.md`'s two writeups
(`fix_e501_merge_introduced` T-1547, `fix_cov002_ticket_directive_
insertion` T-1548 including T-1581's comment-leader-resolution
addition) into `docs/modules/gates.md`'s existing "`--fix` Tier-A
deterministic auto-fix handlers" section, as two new `###` subsections
inserted right before the existing SYS100/SYS104 (T-1531) subsection --
matching that subsection's own shape/heading level, per the ticket's
own precedent. Updated the `frob:describes` anchors and the two
`frob:doc` directives in `src/frob/gates/_fix_engine.py` (on
`fix_e501_merge_introduced` and `fix_cov002_ticket_directive_
<!-- frob:waive DOC006 reason="historical Done report describing the deletion of docs/modules/gates_e501_autofix.md itself, which by definition no longer exists after this ticket landed" -->
insertion`) to point at the new `gates.md` anchors instead of the
deleted page. Then deleted `docs/modules/gates_e501_autofix.md`.

<!-- frob:waive DOC006 reason="historical Done report describing the deletion of docs/modules/gates_e501_autofix.md itself, which by definition no longer exists after this ticket landed" -->
**Deletion-filter declaration**: `docs/modules/gates_e501_autofix.md`
deleted, no `frob:waive` directives present in the deleted file
(confirmed via `grep -n "frob:waive" docs/modules/gates_e501_autofix.md`
before deletion -- zero matches, nothing to re-declare).

Mid-ticket, `frob check --only gates-fast --ticket T-1580` surfaced a
real, pre-existing bug unrelated to this ticket's own diff: `main` had
moved forward with a land (T-1518, landed before this session touched
this worktree) whose own COV002 auto-fix reintroduced the EXACT
Python-style-directive-into-`design/frob.strata` corruption T-1581
(this same session's earlier ticket) fixes going forward -- a hand-
repair commit for THAT specific instance (5bdf02c3, "stop the COV002
auto-fix from corrupting non-Python files at land") had already landed
to `main` by the time I checked, so merging `main` again (after
waiting for an in-flight coordinator land, T-1279, to finish and the
tip to stabilize, per playbook section 1 step 0) picked up the repair
directly -- `design/frob.strata` parses cleanly again, and the
resulting cascade of ~40+ misattributed DRIFT/COV/PARSE findings this
session's `frob check` runs briefly showed is gone. That merge also
conflicted in `src/frob/app/ticket_runner/_land_cmd.py` (this session's
own T-1578 natives-preflight edit vs. main's own interim `COV002`
Tier-A exclusion workaround for the same corruption bug) -- resolved by
keeping BOTH: the COV002 exclusion stays until T-1581's own land
reverts it (avoiding a race between two tickets landing in unknown
order), and T-1578's natives-health check runs alongside it.

Residual, disclosed rather than forced (same shape as this session's
other Done reports): a `--ticket T-1580`-scoped `frob check` still
shows ~21 COV002/COV001 findings and 3 SCOPE-family findings against
files T-1577/T-1578/T-1579/T-1581 touched in this SAME worktree, plus
several unrelated OTHER agents' concurrently-open tickets (T-1582,
T-1396, T-1389, T-1264, T-1554, T-1533, T-1549, T-1545, T-1544, T-1342,
T-1339 -- verified directly: `frob.gates._scope_covers` reports these
paths as "ambiguously covered by N equally-specific open ticket
scopes"). None of this is T-1580's own diff (docs-only, `docs/modules/
gates.md` + the delete) -- it is pre-existing scope-ambiguity noise
from a busy parallel-drive session with many open tickets simultaneously
declaring broad scope over the same large shared files, structurally
outside what a docs-only ticket can or should fix. `frob check
--land-parity` -- the actual land-sweep-equivalent check -- reports
CLEAN (0 unscoped errors) against the current worktree tree both before
and after this ticket's own commit, confirming none of this blocks a
real land.

### Changed
```
 docs/modules/gates.md                     | 187 ++++++++++++--
 docs/modules/gates_e501_autofix.md        |  77 ------
 docs/modules/perf.md                      |  39 +++
 src/frob/app/ticket_runner/_land_cmd.py   |  51 +++-
 src/frob/gates/__init__.py                |  59 +++++
 src/frob/gates/_fix_engine.py             | 198 ++++++++++-----
 src/frob/gates/_fmt_directives.py         |  10 +-
 src/frob/gates/_waive.py                  |  37 ++-
 tests/test_gates.py                       | 139 +++++++++++
 tests/test_gates_fix_engine.py            |  78 ++++++
 tests/test_ticket_work_and_land_finish.py |  61 +++++
 tickets.md                                | 388 +++++++++++++++++++++++++++++-
 12 files changed, 1163 insertions(+), 161 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 553 warning(s), 798 waived
- error-findings: none (measured, zero errors)
