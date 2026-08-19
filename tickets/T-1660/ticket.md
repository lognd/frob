---
id: T-1660
title: 'PERF014 remainder: 3 confirmed real per-line finditer nesting sites (cpp_mayraise,
  ffi, rule_id_scan)'
state: in-progress
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/arch/_cpp_mayraise.py
- src/frob/arch/_ffi.py
- src/frob/gates/_rule_id_scan.py
- tests/test_perf.py
evidence_scope:
- tests/gates/test_rule_id_scan_branches.py
- tests/test_gates.py
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'T-2446: the 3 src files were already precisely scoped (this ticket''s own
    body names them exactly); tests/test_perf.py is the existing general PERF-gate
    test suite (confirmed via ls tests/) -- not a guess'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_perf.py
  reason: 'T-2446: the 3 src files were already precisely scoped (this ticket''s own
    body names them exactly); tests/test_perf.py is the existing general PERF-gate
    test suite (confirmed via ls tests/) -- not a guess'
  actor: logan
  at: '2026-08-18'
body_changes:
- mode: append
  reason: T-1660 is a pure perf restructure with identical observable output; BUG002
    needs this to check PASSED-at-main rather than FAILED-at-main
  actor: logan
  at: '2026-08-18'
  old_length: 1483
  new_length: 1804
evidence:
- tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_commented_out_rule_literal_is_skipped
- tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_const_ref_resolves_against_assignment_in_another_file
- tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_missing_scanned_base_directory_is_skipped_not_an_error
- tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_unresolved_const_ref_is_left_out
- tests/test_gates.py::TestFfiBoundaryGate::test_ctypes_call_with_empty_declaration_clean
- tests/test_gates.py::TestFfiBoundaryGate::test_ctypes_call_without_declaration_fires_ffi002
- tests/test_gates.py::TestKnownGateRuleIds::test_scan_finds_a_synthetic_rule_id
- tests/unit/test_arch.py::test_arch_end_to_end_analyze_then_render
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1649's PERF014 rule-level audit (AST-based ancestor-loop-depth rewrite,
replacing the flat token-count heuristic) reclassified all 9 originally-live
PERF014 findings: 6 were confirmed false positives (flat-count conflated
sequential/comprehension loops with real nesting) and 3 are CONFIRMED real,
genuinely-nested per-line finditer sites that the rewrite correctly keeps
flagging:

- src/frob/arch/_cpp_mayraise.py:371 (_scan_each_function) -- calls
  `_CALL_RE.finditer(line)` inside `for idx, name, qualifiers in sig_lines:
  for line in body: ...` -- 2 real nested levels.
- src/frob/arch/_ffi.py:399 -- same per-function x per-line shape.
- src/frob/gates/_rule_id_scan.py:163 (scan_emitted_rule_ids) -- calls
  `_LITERAL_PATTERN.finditer(line)` inside a 3-level nested walk (per
  SCANNED_BASES dir x per file x per line).

T-1649's own scope only covered the rule-level audit/fix, not fixing these
individually-verified real sites. This ticket is that follow-up: for each,
either restructure to call finditer() once over the whole joined text (with
a newline-offset/bisect line-number recovery, the same technique
src/frob/gates/_docptr.py::_prose_tokens already uses for its own
whole-text finditer scan) instead of once per physical line, or add a
specific, reasoned frob:waive PERF014 if the restructure is not worth the
risk for that site (e.g. genuinely bounded/rare, matching the reasoning
_inv006_split_assist.py's own PERF011 fix carried for its "runs rarely"
site).

frob:no-behavior-change reason="all three PERF014 sites are restructured to a single finditer() call over the whole text (with bisect line-number recovery where a line number is still needed) instead of once per physical line -- pure perf/structural refactor, no output difference, covered by existing regression tests"