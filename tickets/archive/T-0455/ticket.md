---
id: T-0455
title: 'formal scope/lease change protocol: frob ticket scope --add/--remove <glob>
  --reason (expand or reduce a ticket''s work-scope AND its tree-lease), FAILS LOUDLY
  if requested paths are leased by another in-progress ticket -- replaces the ad-hoc
  SCOPE001 waive dodge'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/
- src/frob/app/ticket_runner.py
- src/frob/__main__.py
- docs/modules/tickets.md
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_scope_mutation.py::TestMutateScope::test_add_free_path_granted
- tests/test_tickets_scope_mutation.py::TestMutateScope::test_add_leased_path_rejected_names_holder
- tests/test_tickets_scope_mutation.py::TestMutateScope::test_remove_frees_path_for_other_doable
- tests/test_tickets_scope_mutation.py::TestMutateScope::test_remove_not_declared_rejected
- tests/test_tickets_scope_mutation.py::TestMutateScope::test_remove_orphaning_evidence_rejected
- tests/test_tickets_scope_mutation.py::TestMutateScope::test_empty_change_rejected
- tests/test_tickets_scope_mutation.py::TestMutateScope::test_missing_reason_rejected
- tests/test_tickets_scope_mutation.py::TestMutateScope::test_audit_trail_is_append_only
- tests/test_tickets_scope_mutation.py::TestScopeCli::test_cli_add_free_path
- tests/test_tickets_scope_mutation.py::TestScopeCli::test_cli_add_leased_path_exits_nonzero
- tests/test_tickets_scope_mutation.py::TestScopeCli::test_cli_requires_reason
- tests/test_tickets_scope_mutation.py::TestScopeCli::test_cli_requires_add_or_remove
designated_repro_test: null
threat: null
component: null
---
User request 2026-07-20: agents constantly discover mid-work that the fix
structurally needs files outside their declared scope (a new subcommand
needs __main__.py/config.py; a gate fix needs its test file). Today they
either WAIVE SCOPE001 with the T-0176/T-0220 precedent or the coordinator
widens the scope by hand at landing. There is no formal, accountable
protocol for a scope/lease change. Build one -- and it must fail loudly, not
silently grab another agent's paths (the user's standing "make it hard to do
damage, fail loudly" mandate).

Design (formal scope + lease mutation, ties to T-0453 lease model):
- `frob ticket scope T-#### --add <glob>... --reason "..."` expands the
  ticket's declared `scope` AND its active tree-lease. `--remove <glob>...
  --reason "..."` reduces both (releasing the freed paths back to other
  agents' doable). Every change appends to a `scope_changes:` audit list on
  the ticket ({op, glob, reason, actor, at}) so scope creep is visible and
  accountable, never silent.
- FAILS LOUDLY on conflict: an `--add` whose glob overlaps a path leased by
  ANOTHER in-progress ticket is REJECTED with a clear error naming the
  holding ticket ("cannot lease src/frob/gates/**: held by in-progress
  T-0yyy") -- an agent can never expand into paths another agent is actively
  writing. This is the enforcement that makes parallel work safe.
- Replaces the SCOPE001 waive dodge: instead of `frob:waive SCOPE001
  reason="__main__.py needed for a new subcommand (T-0176 precedent)"`, the
  agent runs `frob ticket scope T-#### --add src/frob/__main__.py --reason
  "new subcommand registration"` -- an honest declared expansion the ledger
  records, not a waiver that hides it. (T-0446 -- the new-subcommand scope
  gap -- becomes a doc example of this flow, not a separate workaround.)
- Guardrails: an expansion still cannot exceed sane bounds (warn on a
  request to `src/frob/**`); a reduction cannot drop a path that already has
  committed changes/evidence bound to it (that would orphan work).
- Acceptance: an agent formally expands its scope to a free path (granted,
  audited) and to a leased path (rejected, names the holder); a reduction
  frees paths and they re-appear in another ticket's T-0453 doable; the
  scope_changes audit shows every mutation with its reason; SCOPE001 no
  longer needs the __main__.py waive dodge for a properly-expanded ticket.