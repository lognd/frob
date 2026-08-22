## Done report

Pure structural split of fix_sys111_capability_ratchet_sync (114 lines, ARCH001) into itself plus a new _apply_capability_ratchet_bumps helper -- zero behavior change (frob:no-behavior-change), verified by the same 3 sys111 tests passing identically before and after.

### Changed
```
 rapid-debt.jsonl                        |  5 +++++
 src/frob/gates/_fix_engine_sync.py      | 28 ++++++++++++++++++++-------
 tickets/T-2013/ticket.md      | 34 +++++++++++++++++++++++++++++++++
 tickets/T-2014/done-report.md | 23 ++++++++++++++++++++++
 tickets/T-2014/ticket.md      | 29 ++++++++++++++++++++++++++++
 tickets/T-2015/done-report.md | 19 ++++++++++++++++++
 tickets/T-2015/ticket.md      | 30 +++++++++++++++++++++++++++++
 7 files changed, 161 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierA::test_sys111_bumps_growth_this_lands_diff_caused` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys111_leaves_a_pre_existing_breach_untouched` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys111_no_design_dir_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/gates/_fix_engine_sync.py, COV003@tickets/T-0907, F401@/home/logan/projects/frob/.claude/worktrees/t2001-follow/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t2001-follow/tests/unit/test_tickets_evidence_only_scope.py
