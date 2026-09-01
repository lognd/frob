---
id: T-3640
title: 'post-T-3592 fallout: self-referential frob:tests directives point at old tests/unit/test_arch.py'
state: queued
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/arch_suite/test_complexity.py
- tests/unit/arch_suite/test_misc.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Same pattern as T-3635 (T-3591's fallout): T-3592's split of tests/unit/test_arch.py into tests/unit/arch_suite/ moved 9 self-referential frob:tests directives (a test citing itself as its own regression-lock evidence) without repointing them -- they still cite tests/unit/test_arch.py::Class.method instead of their own new tests/unit/arch_suite/<module>.py location. Confirmed via 'frob check --only drift' (DRIFT002, 9 hits) on 2026-09-01, in tests/unit/arch_suite/test_complexity.py::TestDeepNestingArchExempt (3 tests) and tests/unit/arch_suite/test_misc.py::TestCppSymrefCanonicalization/TestCppMayThrow (6 tests). Fix: same recipe as T-3635 -- for each hit, replace the self-citing frob:tests path with the test's own current file.