---
id: T-1548
title: 'Tier-A auto-fix: COV002 changed-symbol-without-edge insertion'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
- src/frob/app/ticket_runner/_land_cmd.py
- docs/modules/gates_e501_autofix.md
- tests/test_gates_fix_engine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: the COV002 Tier-A handler needs the landing ticket id, which only the _land_cmd.py
    call sites (_tier_a_pre_land_step / _apply_root_tier_a_fixes) have -- apply_tier_a_fixes
    needs a threaded ticket_id parameter and both call sites need to pass it through
  actor: logan
  at: '2026-08-05'
- op: add
  glob: docs/modules/gates_e501_autofix.md
  reason: COV002 handler doc anchor added to the shared T-1547/T-1548 pending-fold-in
    page (already owned by T-1547 in this same worktree)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/test_gates_fix_engine.py
  reason: COV002 handler tests live in the fix-engine-dedicated test module (already
    owned by T-1547 in this same worktree)
  actor: logan
  at: '2026-08-05'
evidence:
- tests/test_gates_fix_engine.py::TestFixCov002TicketDirectiveInsertion::test_open_landing_ticket_gets_directive_inserted_and_reverifies_clean
- tests/test_gates_fix_engine.py::TestFixCov002TicketDirectiveInsertion::test_no_ticket_id_is_a_no_op
designated_repro_test: null
threat: null
component: null
---
Follow-up from T-1531: insert '# frob:ticket <landing-id>' above a symbol when COV002 (changed-symbol-without-edge) fires and the diff producing it belongs to the landing ticket itself. Needs a Tier-A handler that reads COV002's finding (symbol + file:line) plus the landing ticket id from the caller (both _tier_a_pre_land_step and _apply_root_tier_a_fixes already have it), confirms the changed hunk actually belongs to that ticket's own diff, and inserts the directive line above the symbol.