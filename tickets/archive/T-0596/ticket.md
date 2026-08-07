---
id: T-0596
title: 'gate:PERF: resolve 11 unwaived findings (9x PERF004 sort-in-loop, 2x PERF005
  unprovable recursion)'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_coverage.py
- src/frob/gates/_registry_exhaustiveness.py
- src/frob/strata/_cve_fingerprint.py
- src/frob/tickets/_brief.py
- src/frob/__main__.py
- src/frob/gates/_docblocks.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_main_entry.py::TestDidYouMean::test_unrecognized_flag_suggests_closest_known_flag
- tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_missing_row_for_real_command_fails
- tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_fully_covered_table_passes
- tests/test_waive_gate.py::TestWaive007CommentChannel::test_ticket_attr_bound_to_unresolvable_id_fires
- tests/test_waive_gate.py::TestWaive007StrataChannel::test_strata_ticket_attr_bound_to_unresolvable_id_fires
- tests/test_registry_exhaustiveness.py::TestDuplicateId::test_duplicate_id_across_files_fails
- tests/test_gates.py::TestTick008UnknownLedgerFields::test_fires_on_unknown_field
- tests/test_gates.py::TestTest014AmbiguousConventionMatch::test_fires_on_cross_file_same_test_collision
designated_repro_test: null
threat: null
component: null
---
gate:PERF currently reports 0 errors, 11 warnings, 39 waived (measured 2026-07-22). The 11 unwaived are: 9x PERF004 sorted()/.sort() in a loop (src/frob/gates/__init__.py:1183,2914,4279,4610,4695; src/frob/gates/_coverage.py:545; src/frob/gates/_registry_exhaustiveness.py:405; src/frob/strata/_cve_fingerprint.py:518; src/frob/tickets/_brief.py:118) and 2x PERF005 no-provable-termination recursion (src/frob/__main__.py:92 _collect_option_strings; src/frob/gates/_docblocks.py:386 _subparser_tree). For each PERF004: hoist the sort out of the loop, switch to a sorted container, or waive with a genuine per-site reason (the existing 39 waived findings on this same gate show the expected reason shape -- 'runs once after the loop', 'own iterable not repeated', etc; do not copy a reason that does not actually hold for the new site). For each PERF005: add a frob:invariant terminates reason=... measure=... annotation with a real termination measure, or restructure. Acceptance: gate:PERF summary line reports 0 unwaived findings (fixed or waived-with-reason), no threshold loosened without a disclosed decision.