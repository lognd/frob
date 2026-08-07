## Done report

Investigation found the fix this ticket describes ALREADY PRESENT on
main -- `scope_private_helper_gaps`/`_caller_private_helper_gaps` in
src/frob/graph/callgraph.py already implement the exact same-short-
name same-file suppression the ticket's Description proposes ("require
the SAME leaf-name collision to be genuinely ambiguous before
flagging"), with a docstring explicitly citing T-1012 and two tests
(tests/test_graph.py::TestScopePrivateHelperGaps::
test_flat_dir_same_name_self_match_is_silent/
test_flat_dir_genuine_cross_file_helper_still_fires) already in place
and passing.

`git log -S"T-1012: over a FLAT"` traced this to commit 8069c2d2
("fix(tickets): land T-0823 lang: LANG003 known-gap ticket refs
unresolvable in adopter repos"), which legitimately touched
src/frob/graph/callgraph.py and tests/test_graph.py alongside its own
T-0823 scope (`git show --stat` confirms both files in that commit's
diff) -- this looks like T-1012 was implemented and swept into T-0823's
land, whether by a worktree merge that combined both tickets' work or
a coordinator-side bundling; either way the code is real, committed,
and on main now, not something I need to re-implement. No corresponding
tickets.md/tickets-archive.md Done-report entry credits T-0823 with the
T-1012 fix, so this ticket was left open in the ledger despite the
work already existing -- this Done report formalizes/closes that gap.

Verification (fresh, this session, not re-trusting the old land):
- Re-ran the ticket's own reproduction directly:
  `scope_private_helper_gaps(Path("."), ("tests/test_graph.py",),
  <all tests/*.py files>)` over this repo's real tree now returns 0
  gaps (was 4000+ per the ticket's own filed numbers) -- the noisy
  class is gone.
- `tests/test_graph.py::TestScopePrivateHelperGaps` (all 5 cases,
  including the two T-1012-specific ones) passes: 5 passed.
- `test_flat_dir_genuine_cross_file_helper_still_fires` (already
  existing) confirms the true-positive class T-0998 shipped (a genuine
  cross-file private-helper call with no same-name local candidate)
  is NOT lost by the suppression.
- ruff check clean (both `ruff` and `uv run ruff`) on
  src/frob/graph/callgraph.py (no changes made this ticket, but
  verified as part of closing it).

No code changes made -- this ticket's scope (src/frob/graph/
callgraph.py) already contains the described fix. Recording the two
existing tests as this ticket's evidence.

Filed: none.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_graph.py::TestScopePrivateHelperGaps::test_flat_dir_same_name_self_match_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestScopePrivateHelperGaps::test_flat_dir_genuine_cross_file_helper_still_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 26 error(s), 592 warning(s), 431 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, ARCH001@src/frob/doctor.py, ARCH001@src/frob/tickets/__init__.py, COV001@src/frob/gates/_tracked_files.py, COV003@tickets/T-0138, COV003@tickets/T-0226, COV003@tickets/T-0629, COV003@tickets/T-0700, COV003@tickets/T-0702, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:295, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:111, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:22, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:23, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:35, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:46, INV006@src/frob/app/stats_runner.py, INV006@src/frob/gates/_tickets_gate.py, PII012@src/frob/gates/_tickets_gate.py, PII012@tests/system/test_cli_doctor.py, SELFAUDIT001@design
