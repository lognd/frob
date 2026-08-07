---
id: T-1660
title: 'PERF014 remainder: 3 confirmed real per-line finditer nesting sites (cpp_mayraise,
  ffi, rule_id_scan)'
state: queued
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
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
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