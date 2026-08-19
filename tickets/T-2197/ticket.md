---
id: T-2197
title: frob ticket promote inside a worktree produces an id invisible to the whole
  fleet until that worktree's branch lands
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/tickets/_promote.py
- docs/guides/agent-playbook.md
- src/frob/tickets/_draft_finalize.py
- tests/test_tickets_collision.py
evidence_scope:
- tests/test_tickets_ledger_concurrency.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_draft_finalize.py
  reason: real producer of the commit gap is finalize_draft in frob.tickets, not the
    aspirational _promote.py the ticket named; adding it to scope, keeping _promote.py
    too since it stays a valid home for a new shared helper
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_tickets_collision.py
  reason: existing test file for finalize_draft regression coverage
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_tickets_collision.py::TestPromoteFromWorktreeCommitsAndWarns::test_finalize_draft_commits_the_full_rename_in_a_worktree
- tests/test_tickets_collision.py::TestPromoteFromWorktreeCommitsAndWarns::test_finalize_draft_warns_when_root_is_not_the_primary_checkout
- tests/test_tickets_collision.py::TestPromoteFromWorktreeCommitsAndWarns::test_finalize_draft_in_the_primary_checkout_itself_does_not_warn
- tests/test_tickets_ledger_concurrency.py::TestPromoteVsLandFinalizeAllocationRace::test_promote_and_land_finalize_never_allocate_the_same_id
designated_repro_test: tests/test_tickets_collision.py::TestPromoteFromWorktreeCommitsAndWarns::test_finalize_draft_commits_the_full_rename_in_a_worktree
attachments:
- path: T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md
  caption: self-referential confirmation + two folded-in incidents (silent downstream
    success, T-2196 measured-then-discarded verdict) cross-referenced
  sha256: f5f7da4aa20413df65fb47f85e856abe5a63dbb1e0ff584badbc32f941995e2d
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 696659925a629ff0467720e762f48087237f2050
---
Observed live during T-2188 (2026-08-16). `frob ticket promote T-draft-XXXX`
run inside a per-ticket worktree succeeds, prints a real id (e.g. T-2195),
and every subsequent ticket-CLI action against that id (block, attach,
priority, show) succeeds too -- but the id and every one of those actions
exist ONLY on the worktree's own branch until that branch lands onto
main. `frob ticket work T-2195` (or `doable`, or a dispatch) run against
main's own ledger sees nothing: the ticket file is simply absent, not
merely stale.

This produced a real coordination failure: T-2188 blocked itself on the
newly-promoted T-2195 and handed it off for dispatch, but T-2195 did not
exist on main yet (T-2188's own land was still pending). The coordinator's
own capacity check read an EMPTY `grep -m1 '^state:' tickets/T-2195/
ticket.md` as "not a problem" rather than "this file does not exist",
and dispatched a fresh agent that correctly refused. The gap only closed
once T-2188's worktree branch actually landed.

The dangerous shape: every individual command (`promote`, `block`,
`attach`, `priority`) reports success and looks identical whether the
new id is real (on main) or phantom (worktree-only) -- there is no
warning at ANY of those steps that the id will not be dispatchable until
a land happens. A coordinator or fleet-status script checking for the
ticket's existence via a plain grep gets silence in both the "ticket
genuinely absent" and "ticket exists but file read failed" cases, which
is the same failure shape already named in this repo's own institutional
memory (`grep-on-a-failed-command-reads-as-zero`) -- generalized here to
"grep on an ABSENT file reads as zero", not just a failed command.

WANTED (one or more of, implementer's call after reading the actual
`promote`/`block`/`attach` call sites):

- `frob ticket promote` (and/or `block`/`attach`/`priority` when
  targeting a NOT-yet-landed id) prints a loud, impossible-to-miss
  warning: "T-XXXX exists only on this worktree's own branch until it
  lands -- not yet dispatchable."
- `frob ticket show`/`doable`/`work` on an id that resolves ONLY inside
  a worktree branch (never reached main) distinguishes that from
  "ticket does not exist at all" -- at minimum a different, greppable
  message, ideally a positive "found on branch <name>, not on main"
  signal a coordinator's capacity check could act on instead of reading
  silence.
- `docs/guides/agent-playbook.md` gets a section on this sharp edge
  (worktree-local promote/block/attach visibility) alongside the
  existing ledger-conflict/land-splice guidance, since it is exactly
  the kind of process lesson that section exists to centralize.

Not proposing a specific implementation beyond that -- the right fix
depends on where ticket resolution actually happens (`frob.tickets`
package) and what a coordinator's own capacity-check tooling can
practically consume; that's the implementer's call.