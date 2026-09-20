---
id: T-4633
title: 'SYS111 ratchet ceilings race every land: a ticket that declares a new via
  site bumps accepted_count against a stale dev count, then dev moves and the land
  refuses with ''grew above the committed ceiling''; the land''s composed-tree check
  must auto-accept growth that is exactly the branch''s own declared via additions
  (same posture as the T-4596 testsuite-glob auto-accept)'
state: done
kind: bug
origin: human
created: '2026-09-19'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_effects.py
- src/frob/tickets/_land_squash.py
- docs/modules/gate-sys111-ratchet-auto-accept.md
- tests/strata/test_sys111_auto_accept.py
- tests/unit/strata/test_selfconform.py
- tickets/T-4605/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/_effects.py
  reason: SYS111 auto-accept for branch-own via growth
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/tickets/_land_squash.py
  reason: auto-accept path for ratchet ceiling growth (T-4596 posture)
  actor: logan
  at: '2026-09-19'
- op: add
  glob: docs/modules/gate-sys111-ratchet-auto-accept.md
  reason: standalone doc since docs/modules/gates.md is leased by T-4111
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/strata/test_sys111_auto_accept.py
  reason: positive controls for auto-accept and undeclared-site refusal
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: frob:tests directives for branch-own via growth auto-accept
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tickets/T-4605/ticket.md
  reason: append fold-in note for gate-sys111-ratchet-auto-accept.md, same convention
    as prior lease-conflict fold-ins
  actor: logan
  at: '2026-09-19'
evidence:
- tests/unit/strata/test_selfconform.py::TestBranchOwnViaGrowth::test_branch_own_growth_auto_accepts
- tests/unit/strata/test_selfconform.py::TestBranchOwnViaGrowth::test_own_addition_is_measured
- tests/unit/strata/test_selfconform.py::TestBranchOwnViaGrowth::test_growth_beyond_branch_own_addition_still_refuses
- tests/unit/strata/test_selfconform.py::TestBranchOwnViaGrowth::test_no_head_blob_treats_every_entry_as_added
designated_repro_test: tests/unit/strata/test_selfconform.py::TestBranchOwnViaGrowth::test_branch_own_growth_auto_accepts
acceptance:
- text: A branch whose SYS111 ratchet-ceiling growth is exactly accounted for by its
    own via additions to design/frob.strata auto-accepts at land composed-tree check
    time (lock rewritten with a reason naming the ticket), never outside a land.
  evidence:
  - tests/unit/strata/test_selfconform.py::TestBranchOwnViaGrowth::test_branch_own_growth_auto_accepts
  - tests/unit/strata/test_selfconform.py::TestBranchOwnViaGrowth::test_own_addition_is_measured
  - tests/unit/strata/test_selfconform.py::TestBranchOwnViaGrowth::test_no_head_blob_treats_every_entry_as_added
- text: A branch whose growth includes an undeclared site (or growth another already-landed
    ticket is responsible for) still refuses.
  evidence:
  - tests/unit/strata/test_selfconform.py::TestBranchOwnViaGrowth::test_growth_beyond_branch_own_addition_still_refuses
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
