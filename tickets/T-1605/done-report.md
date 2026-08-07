## Done report

Made the noqa pragma on an over-long frob: directive self-retiring
instead of a permanent ratchet. `_rewrite_directive_run` (new, split out
of `_rewrite_lines_via_runs` to stay under ARCH001's 60-line threshold)
now attempts a clean, word-boundary-only wrap of the run's logical text
with the pragma stripped (`_try_wrap_without_forced_break`, new): if
every resulting physical line fits within the configured limit without
cutting mid-token, that wrap is used and the noqa is dropped -- it was
never load-bearing. Only when no such wrap exists (a genuine single
unbreakable token, e.g. a long dotted pytest node id) is the run passed
through byte-identical with the pragma restored, exactly as T-0985's
original escape hatch did.

Both new private helpers are gated by real tests
(TestNoqaSelfRetiresT1605), and T-0985's own three noqa tests plus its
repo-wide idempotence test still pass unchanged, proving the genuinely-
unwrappable and no-noqa branches are untouched.

Cuts disclosed: T-1605's own ticket text also asked for "a one-time sweep
applying it across the repo" to retire the bulk of the ~3016 existing
noqa pragmas in one dedicated commit. The ticket's own scope (narrowed by
the coordinator before dispatch to _fmt_directives.py/_fix_engine.py/
docs/tests only) does not cover a repo-wide file set, so that sweep was
NOT performed here -- filed as its own ticket (T-1778) instead
of silently dropped or done out-of-scope.

Found beyond the ticket: a plain `frob check --ticket T-1605` reports a
spurious SCOPE001 error against `tickets/T-1605/ticket.md` (the sharded
per-ticket ledger `frob ticket work` auto-commits) on every single ticket
using that layout -- `scope_matches` only treats the legacy `tickets.md`
as implicitly in scope, never the newer per-ticket sharded file. Verified
this does NOT block `frob ticket land` (SCOPE001 is already exempted at
land's own pre-commit checkpoint, T-1524), but it is noise on every
mid-ticket `frob check` an agent runs. Filed as T-1777.

### Changed
```
 tickets/T-1605/ticket.md           |  8 +++++-
 tickets/T-1777/ticket.md | 50 ++++++++++++++++++++++++++++++++++++++
 tickets/T-1778/ticket.md | 37 ++++++++++++++++++++++++++++
 3 files changed, 94 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates_fmt_directives.py::TestNoqaSelfRetiresT1605::test_wrappable_reason_loses_its_noqa` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestNoqaSelfRetiresT1605::test_idempotent_after_dropping_noqa` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestNoqaSuffixPragmaT0985::test_over_long_single_line_with_noqa_e501_is_byte_identical` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestNoqaSuffixPragmaT0985::test_over_long_single_line_with_bare_noqa_is_byte_identical` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestRepoWideIdempotenceT0985::test_canonicalizing_twice_over_real_repo_files_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 765 warning(s), 720 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/agent-a1333f31aa6e06e85/.claude/worktrees/t-1605/src/frob/gates/_fmt_directives.py
