---
id: T-1987
title: land's Tier-A fmt auto-fix rewraps noqa-suppressed frob:waive comments, regressing
  ARCH001
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fmt_directives.py
- tests/test_gates_fmt_directives.py
evidence_scope:
- tests/test_gates_fmt_directives.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates_fmt_directives.py
  reason: test-only repro/regression coverage lives here, matching src/frob/gates/_fmt_directives.py's
    own test module
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_gates_fmt_directives.py::TestNoqaAlwaysPreservedT1987::test_wrappable_reason_keeps_its_noqa
- tests/test_gates_fmt_directives.py::TestNoqaAlwaysPreservedT1987::test_idempotent_with_noqa_kept
designated_repro_test: tests/test_gates_fmt_directives.py::TestNoqaAlwaysPreservedT1987::test_wrappable_reason_keeps_its_noqa
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
land's absorbed Tier-A fmt auto-fix rewrapped a single-line
`# frob:waive WALK001 reason="..."  # noqa: E501` comment inside
frob.graph._walk_repo_files into 4 lines using backslash continuations,
during both the T-1970 and T-1968 lands (2026-08-10). The comment was
already noqa-suppressed and needed no reflow.

The rewrap had two effects:
1. It pushed src/frob/graph/__init__.py::_walk_repo_files from 60 to 63
   lines, tripping ARCH001 (threshold 60) -- a real gate regression on
   main, fixed directly (reverted to the single-line form) as part of
   landing T-1968.
2. Backslash-continued frob:waive/frob:tests comments do not appear to
   be reliably re-parsed as the same single logical directive by every
   scanner -- this is adjacent to, but distinct from, T-1970/T-1968's
   own mention/use-escape work and was not diagnosed further here.

Scope this ticket to find/fix the Tier-A fmt auto-fix handler that
performs this backslash-continuation rewrap (likely in
src/frob/gates/_fmt_directives.py, absorbed into `frob ticket land`
per docs/guides/agent-playbook.md section 0 step 5) so it either skips
already-noqa-suppressed long directive lines, or wraps them in a form
that keeps line-count-sensitive gates (ARCH001) and directive parsing
unaffected.

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
