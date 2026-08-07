---
id: T-0619
title: 'arch: ISP checks (ARCH1xx) -- fat interface, narrow-client usage'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0609
parent: T-0330
tier: ticket
sprint: null
scope:
- src/frob/arch/_solid.py
- src/frob/arch/_models.py
- docs/modules/arch.md
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestFatInterface::test_mostly_stubbed_implementers_flag_fat_interface
- tests/unit/test_arch.py::TestFatInterface::test_mostly_implemented_methods_not_flagged
- tests/unit/test_arch.py::TestNarrowClientUsage::test_client_using_small_method_subset_flagged
- tests/unit/test_arch.py::TestNarrowClientUsage::test_client_using_most_of_interface_not_flagged
- tests/unit/test_arch.py::TestRunIspChecks::test_combines_both_checks
designated_repro_test: null
threat: null
component: null
---
fat interface: ABC/Protocol/trait whose implementers stub most methods with raise NotImplementedError/pass (measured over resolved implementers, not per-class). narrow-client usage: a function/class injected with a wide interface but only calling a small subset of its methods -- flag as an ISP split candidate. Acceptance: positive+negative fixtures; docs updated.