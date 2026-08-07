---
id: T-0248
title: grammar-affecting landings leave stale natives on main -- land/check must detect
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/strata/**
- Makefile
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_native_staleness.py::TestStaleNatives::test_reports_native_grammar_ahead_of_native
- tests/unit/strata/test_native_staleness.py::TestStaleNatives::test_fresh_native_reports_nothing
- tests/unit/strata/test_native_staleness.py::TestStaleNatives::test_unbuilt_native_is_not_reported_as_stale
- tests/unit/strata/test_native_staleness.py::TestStaleNatives::test_no_matching_source_dir_is_not_reported
- tests/unit/strata/test_native_staleness.py::TestStaleNatives::test_default_native_source_dirs_match_repo_convention
- tests/unit/strata/test_native_staleness.py::TestCheckNativeStalenessOrExit::test_exits_nonzero_and_prints_when_stale
- tests/unit/strata/test_native_staleness.py::TestCheckNativeStalenessOrExit::test_returns_none_when_not_stale
- tests/test_ticket_land.py::TestWarnIfNativeStale::test_real_land_logs_stale_native_warning
- tests/test_ticket_land.py::TestWarnIfNativeStale::test_real_land_no_warning_when_native_fresh
designated_repro_test: null
threat: null
component: null
---
Incident during T-0156 review: T-0166 landed a parse.rs grammar change and design/frob.strata began using it, but main's built strata_core predated the change -- frob check reported SYS004 (design failed to load, suppressing SYS001 project-wide) until the coordinator manually ran make core + tool reinstall. Two fixes: (1) frob ticket land detects when the landed diff touches strata-core/**, frob-core/**, or any native-crate source and prints a LOUD post-land instruction (or optionally runs make core) before the final commit; (2) the SYS004 message should distinguish 'parse failed with unknown construct X' and hint that a grammar/native version mismatch is the likely cause when the construct is recognized by the python-side surface docs. Regression: fixture simulating a grammar-ahead-of-native state asserting the hint appears.