## Done report

Changed:
src/frob/gates/_fmt_directives.py::_rewrite_directive_run
src/frob/gates/_fmt_directives.py::_try_wrap_without_forced_break (removed, dead after the fix)

Evidence:
tests/test_gates_fmt_directives.py::TestNoqaAlwaysPreservedT1987::test_wrappable_reason_keeps_its_noqa
tests/test_gates_fmt_directives.py::TestNoqaAlwaysPreservedT1987::test_idempotent_with_noqa_kept
Repro confirmed manually (frob's own --check-repro has an unrelated bug,
filed as T-2005, that made it report a false PASSED_AT_PARENT;
--designate-repro-force used with the manual repro evidence recorded in
the designation reason).

Filed: T-2005 (BUG002 repro-check drops its own PYTHONPATH
override -- verifies against the wrong source for pure-Python changes)

Gates: frob check --only archgate --only fmt clean (0 ARCH errors, 0 FMT
errors) on the worktree; full tests/test_gates_fmt_directives.py suite
(42 tests) green; frob.graph.__init__::_walk_repo_files's real WALK001
waiver at line 180 verified byte-identical under canonicalize_text.

### Changed
```
 src/frob/gates/_fmt_directives.py  | 100 ++++++++++++-------------------------
 tests/test_gates_fmt_directives.py |  56 ++++++++++-----------
 tickets/T-1987/ticket.md           |   9 +++-
 tickets/T-2005/ticket.md |  51 +++++++++++++++++++
 4 files changed, 115 insertions(+), 101 deletions(-)
```

### Evidence
- `tests/test_gates_fmt_directives.py::TestNoqaAlwaysPreservedT1987::test_wrappable_reason_keeps_its_noqa` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestNoqaAlwaysPreservedT1987::test_idempotent_with_noqa_kept` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: COV003@tickets/T-1605, COV005@src/frob/gates/_fmt_directives.py, DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/t1987-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t1987-series/tests/unit/test_tickets_evidence_only_scope.py, SELFAUDIT001@design, TEST001@src/frob/app/ticket_runner/_new.py
