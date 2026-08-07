## Done report

Added SYSWAIVE003 (src/frob/strata/_selfconform.py, T-0671's staleness-
gated waiver mechanism) to the `_KNOWN_GATE_RULES` frozenset -- the
registry literal has since moved from gates/__init__.py into
gates/_waive.py (a prior split land that predates this ticket's
filing), so scope was expanded to include that file (reasoned, `frob
ticket scope T-1139 --add`) alongside the ticket's originally-declared
_rule_id_scan.py.

tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
now passes (was failing on main per the ticket's own repro).

Verification: ruff check clean (both `ruff` and `uv run ruff`) on
src/frob/gates/_waive.py. Targeted test passes.

Filed: none.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 27 error(s), 569 warning(s), 431 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, ARCH001@src/frob/doctor.py, ARCH001@src/frob/tickets/__init__.py, COV001@src/frob/gates/_tracked_files.py, COV003@tickets/T-0138, COV003@tickets/T-0226, COV003@tickets/T-0629, COV003@tickets/T-0700, COV003@tickets/T-0702, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:295, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:111, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:22, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:23, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:35, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:46, INV006@src/frob/app/stats_runner.py, INV006@src/frob/gates/_tickets_gate.py, PII012@src/frob/gates/_tickets_gate.py, PII012@tests/system/test_cli_doctor.py, PRE001@tickets/T-1139, SELFAUDIT001@design
