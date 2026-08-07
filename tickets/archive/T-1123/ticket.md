---
id: T-1123
title: 'arch: extract remaining tickets/__init__.py families + split _land.py -- T-1108
  residue'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- docs/modules/tickets.md
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_scope_mutation.py::TestMutateScope::test_add_free_path_granted
- tests/test_tickets_scope_mutation.py::TestMutateScope::test_add_leased_path_rejected_names_holder
- tests/test_tickets_scope_mutation.py::TestMutateScope::test_remove_frees_path_for_other_doable
- tests/test_tickets_scope_mutation.py::TestNewFileCarveOut::test_new_file_under_broad_lease_is_exempt
- tests/test_tickets_scope_mutation.py::TestNewFileCarveOut::test_existing_file_under_broad_lease_still_conflicts
- tests/test_tickets_scope_mutation.py::TestNewFileCarveOut::test_new_file_exact_match_of_holder_scope_still_conflicts
designated_repro_test: null
threat: null
component: null
---
T-1108 extracted ONE family (doable/leases/scope-breadth: doable, doable_blocked,
leased_by, large_glob_warnings, has_live_lease, dispatch_stale_hours,
undispatched_stale, display_state, scope_breadth_context, and their private
helpers) into src/frob/tickets/_doable.py. tickets/__init__.py dropped from
3489 to 2918 lines (571 carved) -- still above the acceptance criterion's
<2000 target.

Remaining per T-1108's own scope note (~7 families now, one done):
- scope mutation (mutate_scope and its private helpers)
- field setters/sprint (set_priority/set_kind/set_tier/set_sprint/set_component,
  sprint_view/sprint_velocity)
- evidence/transition (transition, add_evidence, the _done_transition_* guard
  family) -- BEWARE the load-time circular import T-1103's Done report flagged
  for this exact family (new_ticket/finalize_draft already late-import from
  the package to work around it)
- done-report/review/drop/attach (brief_ticket, mutate_labels, record_review,
  attach, drop helpers)

_land.py (4762 lines) was not touched at all -- still needs its own split
(preflight/splice/verify/sweep families per T-1108's plan) before LARGE001
stops flagging it.

Follow the same pattern T-1103/T-1108 established: one cohesive family per
dispatch, private module re-exported from __init__ via explicit imports
(never `import *`), zero caller-visible behavior change, existing tests as
the safety net, watch for tests that monkeypatch a moved function via the
PACKAGE attribute (`tickets_mod.<name>`) -- those need a late
`from frob.tickets import <name>` inside the moved function body instead of
a module-top-level binding, or the monkeypatch silently stops taking effect.