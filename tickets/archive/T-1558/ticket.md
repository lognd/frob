---
id: T-1558
title: 'WIRE001 module-local test-helper false-positive class: teach the gate or wire
  the helpers (T-1490/T-1488 successor, waiver home)'
state: done
kind: docs
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_wire.py
- tests/test_cache_transparency.py
- tests/test_cache_gate.py
- tests/test_ticket_land.py
- tests/unit/test_coverage_attribution_lock_t1395.py
- tests/test_tickets_migration.py
- tests/_cache_transparency.py
- tests/unit/perf/test_hotpath_smells.py
- tests/unit/perf/test_serial_pools_import_failure.py
- tests/test_gates.py
- docs/modules/gates.md
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_wire.py
  reason: 'T-1558 acceptance: teach WIRE001''s reachability scan for cross-test-file
    usage, and rebind/delete the 16 named waivers'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_cache_transparency.py
  reason: 'T-1558 acceptance: teach WIRE001''s reachability scan for cross-test-file
    usage, and rebind/delete the 16 named waivers'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_cache_gate.py
  reason: 'T-1558 acceptance: teach WIRE001''s reachability scan for cross-test-file
    usage, and rebind/delete the 16 named waivers'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'T-1558 acceptance: teach WIRE001''s reachability scan for cross-test-file
    usage, and rebind/delete the 16 named waivers'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_coverage_attribution_lock_t1395.py
  reason: 'T-1558 acceptance: teach WIRE001''s reachability scan for cross-test-file
    usage, and rebind/delete the 16 named waivers'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_tickets_migration.py
  reason: 'T-1558 acceptance: teach WIRE001''s reachability scan for cross-test-file
    usage, and rebind/delete the 16 named waivers'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/_cache_transparency.py
  reason: 'T-1558 acceptance: teach WIRE001''s reachability scan for cross-test-file
    usage, and rebind/delete the 16 named waivers'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/perf/test_hotpath_smells.py
  reason: 'T-1558 acceptance: teach WIRE001''s reachability scan for cross-test-file
    usage, and rebind/delete the 16 named waivers'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/perf/test_serial_pools_import_failure.py
  reason: 'T-1558 acceptance: teach WIRE001''s reachability scan for cross-test-file
    usage, and rebind/delete the 16 named waivers'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_gates.py
  reason: 'T-1558 acceptance: teach WIRE001''s reachability scan for cross-test-file
    usage, and rebind/delete the 16 named waivers'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-1558 acceptance: teach WIRE001''s reachability scan for cross-test-file
    usage, and rebind/delete the 16 named waivers'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: 'coordinator directive: T-1698''s rapid-debt fix left a WIRE001 waiver on
    _seed_repo bound to T-1558 as follow_up; rebind onto T-1592''s permanent=true
    mechanism as part of landing this fix, same as the other 13 same-file-only waivers
    this ticket already swept'
  actor: logan
  at: '2026-08-06'
evidence:
- tests/test_gates.py::TestWireGate::test_shared_test_fixture_called_from_a_sibling_test_file_is_not_flagged
- tests/test_gates.py::TestWireGate::test_test_helper_called_only_from_a_non_test_helper_is_still_flagged
designated_repro_test: null
acceptance:
- text: GIVEN a module-local pytest helper (fixture factory, git-init scaffold, parametrized-data
    builder) with no direct call-site the callgraph can see THEN WIRE001 either recognizes
    the pytest usage pattern natively or the helper is wired/bound explicitly -- and
    the 16 waivers currently binding here are deleted
  evidence:
  - tests/test_gates.py::TestWireGate::test_shared_test_fixture_called_from_a_sibling_test_file_is_not_flagged
  - tests/test_gates.py::TestWireGate::test_test_helper_called_only_from_a_non_test_helper_is_still_flagged
threat: null
component: null
---
Successor to T-1490 and T-1488, which closed while 16 frob:waive WIRE001 directives still named them, orphaning the waivers into WIRE002 errors (2026-08-05 incident). This ticket is the OPEN waiver home those 16 directives rebind to; it stays open until the class is actually resolved. Siblings: T-1503 (extract_native golden helpers), T-1534 (autouse fixtures).