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