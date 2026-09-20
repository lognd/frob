---
id: T-4312
title: Warn at ticket-close time when closing strands a live WIRE001 follow_up waiver
state: done
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/gates/_wire.py
- src/frob/tickets/_evidence.py
- tests/unit/test_land_stranding_t4312.py
- tickets/T-4347/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: T-4312 generalizes the strand check across frob:waive/todo/debt/deprecated;
    the single correct wiring point covering close+drop+any terminal transition uniformly
    is frob.tickets._evidence.transition, not per-CLI-command call sites (close_cmd.py,
    _reporting.py) which would duplicate the hook
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_land_stranding_t4312.py
  reason: new test file covering the T-4312 stranding-check generalization (unit dispatch-table
    coverage + end-to-end close/drop force-the-condition tests)
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tickets/T-4347/**
  reason: T-4347 was filed and dropped as a routine side effect of T-4312's own investigation
    (see Done report); its bookkeeping shard needs to be in T-4312's scope for SCOPE001
    to resolve cleanly since the auto-exemption path did not fire for this specific
    file+promote+drop lifecycle
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tickets/T-4347/**
  reason: T-4347 was filed and dropped as a routine side effect of T-4312's own investigation
    (see Done report); its bookkeeping shard needs to be in T-4312's scope for SCOPE001
    to resolve cleanly since the auto-exemption path did not fire for this specific
    file+promote+drop lifecycle
  actor: logan
  at: '2026-09-08'
body_changes:
- mode: append
  reason: 'T-4312: warn at close/drop time when the transition strands a live

    directive naming the ticket being closed. T-4305 repaired one instance

    after the fact (a frob:waive WIRE001 ... follow_up="T-4274" orphaned

    the moment T-4274 closed, turning a passing WIRE002 into a CI-blocking

    failure with zero code changes); T-4316 repaired a second, unrelated

    instance the same day (frob:todo T-4298 orphaned by T-4298''s own close,

    failing TODO002). Neither strand had anything to do with WIRE001

    specifically -- the mechanism is generic: ANY directive family whose

    own gate later checks "does this named ticket id still resolve to an

    OPEN ticket" can be stranded by an unrelated ticket''s close/drop.


    Posture (per the ticket''s own design points): WARN, never REFUSE. A

    warning that scrolls past unread is how both T-4305 and T-4316''s

    strands reached CI in the first place, so every site is named

    individually -- file, line, the exact directive, the gate rule it will

    trip, and the remedy -- in the same log line, not a bare "something now

    dangles" count. A refusal here would block a legitimate close/drop over

    an ENTIRELY UNRELATED ticket''s directive, which is worse than the miss

    it replaces; this mirrors frob.tickets._reporting.reopen_ticket''s own

    T-4287 disclosure (_worktrees_carrying_terminal_copy) -- "disclosure,

    not a second gate."'
  actor: logan
  at: '2026-09-19'
  old_length: 800
  new_length: 2394
evidence:
- tests/unit/test_land_stranding_t4312.py::TestStrandReferenceForEdge::test_waive_wire001_follow_up_is_found
- tests/unit/test_land_stranding_t4312.py::TestStrandReferenceForEdge::test_todo_directive_is_found
- tests/unit/test_land_stranding_t4312.py::TestStrandReferenceForEdge::test_debt_ticket_is_found
- tests/unit/test_land_stranding_t4312.py::TestStrandReferenceForEdge::test_deprecated_ticket_is_found
- tests/unit/test_land_stranding_t4312.py::TestStrandReferenceForEdge::test_unrelated_edge_kinds_are_silent
- tests/unit/test_land_stranding_t4312.py::TestStrandingWarningLines::test_message_names_file_line_directive_rule_and_remedy
- tests/unit/test_land_stranding_t4312.py::TestTransitionWarnsOnStranding::test_drop_warns_on_stranded_waive_follow_up
- tests/unit/test_land_stranding_t4312.py::TestTransitionWarnsOnStranding::test_close_warns_on_stranded_todo
- tests/unit/test_land_stranding_t4312.py::TestTransitionWarnsOnStranding::test_close_with_no_referencing_directives_is_silent
- tests/unit/test_land_stranding_t4312.py::TestTransitionWarnsOnStranding::test_drop_warns_on_stranded_todo
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4305 fixed one WIRE001 waiver stranded when its named follow_up ticket (T-4274) closed, turning a passing WIRE002 check into a CI-blocking failure with zero code changes. Nothing warns at close time: any ticket close can silently strand any frob:waive WIRE001 follow_up="T-####" naming it, discovered only later by a WIRE002 failure (or worse, on main/CI) that gives no hint the true cause was an unrelated ticket close. Add a check at 'frob ticket close'/'frob ticket land' time that scans live frob:waive WIRE001 directives for follow_up= references to the ticket being closed and warns (or blocks) so the closer can either add permanent="true" (if the waiver reasoning is structural, per T-1592's precedent) or repoint follow_up at a still-open ticket before the strand happens instead of after.

<!-- narrative-moved:src/frob/tickets/_land.py:5769:T-4312 -->
T-4312: warn at close/drop time when the transition strands a LIVE
directive naming the ticket being closed. T-4305 repaired one instance
after the fact (a `frob:waive WIRE001 ... follow_up="T-4274"` orphaned
the moment T-4274 closed, turning a passing WIRE002 into a CI-blocking
failure with zero code changes); T-4316 repaired a second, unrelated
instance the same day (`frob:todo T-4298` orphaned by T-4298's own
close, failing TODO002). Neither strand had anything to do with WIRE001
specifically -- the mechanism is generic: ANY directive family whose own
gate later checks "does this named ticket id still resolve to an OPEN
ticket" can be stranded by an unrelated ticket's close/drop. The full
set of such families, cross-checked against `frob.graph.dsl`'s edge
vocabulary and each family's own gate:

Posture (per the ticket's own design points): WARN, never REFUSE. A
warning that scrolls past unread is how both T-4305 and T-4316's strands
reached CI in the first place, so every site is named individually --
file, line, the exact directive, the gate rule it will trip, and the
remedy -- in the same log line, not a bare "something now dangles"
count. A refusal here would block a legitimate close/drop over an
ENTIRELY UNRELATED ticket's directive, which is worse than the miss it
replaces; this mirrors `frob.tickets._reporting.reopen_ticket`'s own
T-4287 disclosure (`_worktrees_carrying_terminal_copy`) -- "disclosure,
not a second gate."
---------------------------------------------------------------------------