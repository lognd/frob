## Done report

Computed own_obligations_clean in _close_own_obligations_for_ticket
(frob.app.ticket_runner._close_cmd) and wired it into
_close_guards_for_ticket, so both `frob ticket close` and `frob ticket
reverify` now pass it to transition()/reverify_close_guard(). Uses
working_diff(root, "main") to get the ticket's OWN diff-touched files;
returns None (skip) when there is no diff to check against. Checks three
things: (a)/(b) COV001 (missing frob:doc edge) and SELFAUDIT001 (missing
testsuite strata declaration), via one `frob check --only gates` spawn
whose repo-wide (rule, file) identities are filtered to the ticket's own
touched files (--ticket does not scope these families, per T-1351), and
(c) REL001 (an outstanding version bump), reusing land's own read-only
`_required_release_bump` directly rather than duplicating the
diff_class/required_version logic. Split into
_own_obligations_rel_bump_dirty/_own_obligations_diff_findings to stay
under ARCH001's line threshold.

Scoping is deliberately conservative: a touched file carrying a
PRE-EXISTING COV001/SELFAUDIT001 finding this ticket did not itself
introduce also counts against it (stricter than "only symbols this ticket
newly added" -- true new-symbol-only diff parsing was out of reach at
this effort level, and the remedy is identical either way for a file the
ticket is already touching).

Verification of the T-1377/T-1379/T-1381 residue class: added
TestCloseRefusesOwnObligationsEndToEnd, driving the REAL `frob ticket
close` entry point against a ticket whose diff touches a file the
(monkeypatched) `frob check --only gates` reports a live COV001 finding
under. Before this ticket, own_obligations_clean was never computed
(always None/permissive) and this closed done; the test now confirms
SystemExit and the ticket staying in-progress, with a clean-diff sibling
test confirming the same path still closes once genuinely clean.
TestCloseOwnObligationsForTicket covers the helper's own None/False/True
matrix for each of the three obligations independently.

Also fixed a real pre-existing regression this change (and T-1410's
identical prior addition) surfaced: tests/unit/test_app_runners_
t0976_mutation_evidence.py's TestCloseGuardsMutationEvidenceDowngrade
unpacked _close_guards_for_ticket's return into a fixed 4-tuple and
passed object() as the ticket, which crashed once the tuple grew to
5/6 items and the two new guards tried to read .acceptance off a bare
object(). Updated the test to stub both new guards to None like the
others; this file landed already (swept into T-1410's own land commit
as an uncommitted worktree change), so the fix here is the delta on top
of that.

Note on process: T-1410 landed from this same shared worktree while
T-1387's own_obligations_clean code was still uncommitted, so `frob
ticket land T-1410`'s pre-merge wip-commit swept T-1387's code changes
into T-1410's landed commit too (T-1338-class hazard -- should have
committed T-1387's work or landed T-1410 before starting T-1387's edits).
The code and tests are correct and now on main either way; a subsequent
`git merge main` in this worktree (needed to clear T-1410's files off
T-1387's SCOPE001 diff) also reverted T-1387's in-progress transition/
evidence/scope-additions to their pre-start state (the exact T-1022 edge
case documented in the playbook, section 10b item 7) -- re-ran `frob
ticket start T-1387`, `frob ticket scope --add`, and `frob ticket
evidence` to restore them; this Done report and its evidence bindings are
the recovered, current state.

Not run as part of this ticket (coordinator-only per playbook section
3c/6b): the full unscoped suite and make coverage.

### Changed
```
 tickets.md | 29 ++++++++++++++++++++++++-----
 1 file changed, 24 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket::test_no_touched_files_skips_the_check` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket::test_diff_unavailable_skips_the_check` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket::test_dirty_cov001_under_touched_file_returns_false` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket::test_rel001_bump_outstanding_returns_false` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket::test_clean_diff_and_no_bump_returns_true` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseRefusesOwnObligationsEndToEnd::test_close_refuses_when_own_diff_leaves_cov001_outstanding` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseRefusesOwnObligationsEndToEnd::test_close_succeeds_once_the_diff_is_actually_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket::test_dirty_selfaudit001_under_touched_file_returns_false` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 2 error(s), 400 warning(s), 697 waived
- error-findings: OPAQUE001@tests/unit/test_ticket_close_own_obligations_t1387.py, PRE001@tickets/T-1387
