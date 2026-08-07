---
id: T-1592
title: WIRE001 waivers on permanently-unwired private test helpers should not require
  an open follow_up
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_wire.py
- tests/**
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestWireGate::test_wire002_clean_when_permanent_true_on_private_test_helper
- tests/test_gates.py::TestWireGate::test_wire002_still_fires_when_permanent_true_outside_tests_tree
- tests/test_gates.py::TestWireGate::test_wire002_still_fires_when_permanent_true_on_public_test_symbol
- tests/unit/test_mutation_sweep_queue.py::TestEnqueuePendingSweep::test_enqueue_persists_entry
designated_repro_test: null
threat: null
component: null
---
A WIRE001 waiver must name an OPEN follow_up ticket (WIRE002 fires when it names a done one). That is right for "this symbol is not wired up YET" -- but wrong for a private test-seed helper used only by its own file's test methods, where having no production caller is the permanent, intended design. Such a waiver has no real follow-up work to point at, so it gets bound to whatever ticket happened to be open at the time and turns into a WIRE002 orphan the moment that ticket closes.

Live instance: tests/unit/test_mutation_sweep_queue.py::_make_ticket named T-1518, which landed, so main now carries a WIRE002 error for a waiver whose own reason states the condition is permanent by design. tests/unit/test_ticket_file_flags.py has the identical _make_ticket precedent.

Fix: let a WIRE001 waiver declare permanence instead of a follow-up -- an explicit permanent=true attribute (or a reason-preset the gate recognizes) that satisfies WIRE002 without naming a ticket, restricted to private symbols under the test tree so production code cannot use it to dodge real wiring. Then sweep the existing test-helper waivers onto it.

Related: T-1559 closed the other half of this class (refusing/auto-migrating orphaned follow_up waivers at close/land time). This is the same problem approached from the other side: some waivers should never have needed a follow-up at all.