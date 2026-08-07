---
id: T-1034
title: Wire cpp-noexcept-throws (T-0687) into an enforced gates/** finding
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/test_arch_gate.py
- docs/modules/gates.md
- src/frob/arch/_cpp_mayraise.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_arch_gate.py
  reason: add CPPTHROW001 gate-wiring evidence tests
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/gates.md
  reason: add CPPTHROW001 rule-catalog row
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/arch/_cpp_mayraise.py
  reason: fix ARCH001 (69 lines, threshold 60) introduced by T-0687's own scan_cpp_functions,
    surfaced now that this ticket's archgate wiring runs the ARCH family against this
    file
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_arch_gate.py::TestArchGateCppThrow::test_noexcept_with_catch_all_does_not_fire_cppthrow001
- tests/test_arch_gate.py::TestArchGateCppThrow::test_cppthrow001_is_waivable_with_reason
- tests/test_arch_gate.py::TestArchGateCppThrow::test_noexcept_may_throw_fires_cppthrow001_error
designated_repro_test: null
threat: null
component: null
---
T-0687 landed frob.arch._cpp_mayraise.check_cpp_noexcept_violations, wired into analyze_project's live cpp dispatch branch, producing ArchSuggestion(category=cpp-noexcept-throws, severity=error). Promoting this into an enforced, unwaivable src/frob/gates/** gate finding (the way frob.gates._unwaivable_channel_rules already does for every other ArchCategory) was out of T-0687's declared scope (arch/**, lang/**, tests/unit/test_arch.py only). Wire it the same way EXHAUST001/002 (T-0688) and errors-as-values-recommended eventually will be.