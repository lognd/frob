## Done report

Finished T-1099's parse.rs -> parse/mod.rs evidence-path migration:
mechanical path-only substitution
`strata-core/src/parse\.rs::tests::` -> `strata-core/src/parse/mod.rs::tests::`
across the 40 remaining occurrences in tickets-archive.md (the "Changed:"
bullet-list form T-1099's earlier sed pass, targeted at the "Evidence:"
form, had missed). No narrative content touched -- `git diff --stat`
shows exactly 40 insertions/40 deletions, one line changed per line.

Verification: `grep -c` confirms 0 remaining `strata-core/src/parse.rs`
occurrences and 101 `strata-core/src/parse/mod.rs` occurrences (61
already-fixed + 40 fixed here) in tickets-archive.md.
`frob check --only coverage` (fresh, full-repo, not scoped) reports 0
COV003 violations (was 40, one per T-0138/T-0226/T-0629/T-0700/T-0702
and siblings' stale evidence ids) -- confirmed by both a `--json` scan
filtered on `code == "COV003"` and a plain-text grep for
`parse.rs`/`parse/mod` mentions in the check output (neither matches
now).

Filed: none.

### Changed
```
 tickets-archive.md | 80 +++++++++++++++++++++++++++---------------------------
 tickets.md         |  3 +-
 2 files changed, 41 insertions(+), 42 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 21 error(s), 546 warning(s), 431 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, ARCH001@src/frob/doctor.py, ARCH001@src/frob/tickets/__init__.py, COV001@src/frob/gates/_tracked_files.py, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:295, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:111, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:22, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:23, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:35, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:46, INV006@src/frob/app/stats_runner.py, INV006@src/frob/gates/_tickets_gate.py, PII012@src/frob/gates/_tickets_gate.py, PII012@tests/system/test_cli_doctor.py, SELFAUDIT001@design
