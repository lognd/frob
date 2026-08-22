## Done report

Further ARCH001 split, extracting _archive_design_dir_at_head and _raw_capability_ratchet_lock -- zero behavior change (frob:no-behavior-change), verified by the same 3 sys111 tests plus full tests/test_gates.py (708 tests) passing identically.

### Changed
```
 tickets/T-2020/ticket.md | 35 +++++++++++++++++++++++++++++++++++
 1 file changed, 35 insertions(+)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierA::test_sys111_bumps_growth_this_lands_diff_caused` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys111_leaves_a_pre_existing_breach_untouched` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys111_no_design_dir_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: COV003@tickets/T-0907, F401@/home/logan/projects/frob/.claude/worktrees/t2001-arch2/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t2001-arch2/tests/unit/test_tickets_evidence_only_scope.py
