## Done report

SUPPRESS001 ty/mypy diagnostic correlation resolved each diagnostic path against the check root a second time when the root was itself nested (worktree under .claude/worktrees), producing root/.claude/worktrees/x/.claude/worktrees/x/... and a could-not-read WARNING for every diagnostic, a silent zero inside agent worktrees. Fix in src/frob/gates (see commits 7e19bed77, 0d7165e74, 88739e04d): resolve once against cwd, absolute stays absolute; DEBUG log of the resolved path; WARNING kept for a genuinely missing file. Repro test fails at parent. Ticket-scoped frob check skipped by coordinator decision (fleet load); land's own check is the gate. Implementer terminated by login expiry after binding evidence; Done report written by the coordinator.

### Changed
```
 src/frob/gates/_suppress.py               | 31 ++++++++---
 tests/test_gates_suppress.py              | 34 +++++++++++-
 tests/unit/test_suppress_worktree_path.py | 87 +++++++++++++++++++++++++++++++
 tickets/T-4493/ticket.md                  | 29 ++++++++++-
 4 files changed, 169 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/unit/test_suppress_worktree_path.py::TestRelativizeUnderNestedWorktreeRoot::test_correlate_reads_the_real_file_under_nested_root` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
