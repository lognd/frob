---
id: T-0182
title: per-operation fire+negative fixture parametrization for the full DANGEROUS_OPERATIONS
  table (T-0158 deliverable 3 remainder)
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_capability_registry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_capability_registry.py::TestPerOperationFireFixtures::test_entry_fires_scan_file_operations
- tests/test_capability_registry.py::TestPerOperationFireFixtures::test_entry_fires_scan_file_capabilities
- tests/test_capability_registry.py::TestPerOperationFireFixtures::test_entry_absent_from_benign_source
designated_repro_test: null
threat: null
component: null
---
T-0158's test_capability_registry.py::_FIRE_FIXTURES covers one representative fire fixture per patterned (kind, language) matrix cell (29 cells), proving the compiled _PATTERNS table fires at least once per cell. It does NOT give every one of the ~70 individual DANGEROUS_OPERATIONS entries (e.g. python has 4 separate exec-kind entries: subprocess, os.system/popen/exec*, os.spawn*, webbrowser.open -- only one fires today) its own dedicated fixture, which is what T-0158 deliverable (3)'s literal text asks for ('for every patterned cell, a minimal real code snippet' read loosely as cell-level, but the addendum's per-operation structure implies per-entry proof would be stronger). Left as a follow-up: parametrize directly over DANGEROUS_OPERATIONS entries (one needle-based fixture per entry) rather than the current per-cell sampling, so a new operation added to the registry without a matching fixture fails loudly (T-0145 drift-lock style) instead of silently riding on a sibling entry's cell-level fixture.