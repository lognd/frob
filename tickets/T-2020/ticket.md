---
id: T-2020
title: 'ARCH001: T-2013''s own split still left two helpers over the 60-line threshold'
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
- src/frob/gates/_fix_engine_sync.py
evidence_scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestFixEngineTierA::test_sys111_bumps_growth_this_lands_diff_caused
- tests/test_gates.py::TestFixEngineTierA::test_sys111_leaves_a_pre_existing_breach_untouched
- tests/test_gates.py::TestFixEngineTierA::test_sys111_no_design_dir_is_a_no_op
designated_repro_test: tests/test_gates.py::TestFixEngineTierA::test_sys111_bumps_growth_this_lands_diff_caused
threat: null
component: null
anchor: false
anchor_reason: null
---
Post-land ARCH001 residue on T-2013's own split: both new helper
functions (_capability_counts_at_head, _apply_capability_ratchet_bumps)
individually exceeded the 60-line threshold. Split further:
_archive_design_dir_at_head (the git-archive-and-extract mechanics) and
_raw_capability_ratchet_lock (the parsed-JSON-with-entries-key loader).

frob:no-behavior-change reason="pure ARCH001 structural split, extracting the git-archive-and-extract mechanics and the raw-JSON-load mechanics into two new tiny helpers -- no executable logic changed, verified by the same 3 sys111 tests plus the full tests/test_gates.py suite (708 tests) passing identically before and after"

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
