---
id: T-0347
title: wire T-0248 stale-native detection into frob check's SYS004 gate message
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/strata/_design_load.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestSysGate::test_sys004_names_stale_native_as_likely_remedy
- tests/test_gates.py::TestSysGate::test_sys004_load_failure
- tests/test_gates.py::TestSysGate::test_sys004_suppresses_sys001
designated_repro_test: null
threat: null
component: null
---
T-0248 built frob.strata._native_staleness (stale_natives/stale_native_warning/check_native_staleness_or_exit) and wired it into frob ticket land (LOUD warn, non-blocking) and make check (Makefile pre-step, fails loudly). Out of T-0248's scope (src/frob/gates/__init__.py is not in its scope globs): fold the same detection into frob check's own SYS004 rendering (_sys004 in gates/__init__.py) so a stale native produces a message distinguishing 'design file failed to parse with unknown construct X, likely a grammar/native version mismatch -- run make core' from a genuine syntax error in the .strata file itself, per the original T-0166 incident's fix (2). Regression: fixture simulating a grammar-ahead-of-native state where a .strata file uses a construct the OLD built strata_core does not recognize, asserting SYS004's message names make core as the likely remedy.