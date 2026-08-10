---
id: T-1867
title: Wire frob ticket anchor CLI + doable-output disclosure (T-1856 follow-up)
state: in-progress
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_mutate.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/_cli_parsers/_ticket/__init__.py
- tests/unit/test_ticket_anchor_cli.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/_doable.py
  reason: 'Narrowing to the anchor-CLI half only, per coordinator direction: _query.py
    is leased by T-1882 and _doable.py is about to be taken by T-1883, both in the
    ledger-identity worktree. The doable-output disclosure half will be filed as its
    own follow-up rather than waiting on either lease.'
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/app/ticket_runner/_query.py
  reason: 'Narrowing to the anchor-CLI half only, per coordinator direction: _query.py
    is leased by T-1882 and _doable.py is about to be taken by T-1883, both in the
    ledger-identity worktree. The doable-output disclosure half will be filed as its
    own follow-up rather than waiting on either lease.'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_ticket/__init__.py
  reason: The metadata-command parser registration list lives here (register_ticket_metadata_parsers)
    -- adding the new anchor subparser call site requires touching this file, alongside
    _add_ticket_anchor_parsers own definition in the already-declared _metadata.py.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_ticket_anchor_cli.py
  reason: New CLI-wiring regression test for the anchor verb, in the standard tests/unit/
    location for a new small feature test module.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001/SYS104 requires the new public _anchor symbol (imported cross-node
    by the CLI dispatch table) declared in the cli nodes interface= list, and the
    new test files fs.write capability declared for testsuite.
  actor: logan
  at: '2026-08-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1856 added the first-class `anchor`/`anchor_reason` fields on `Ticket`
(src/frob/tickets/_models.py), `set_anchor` (src/frob/tickets/_land.py,
library-level set/clear with a required --reason-shaped argument), and
the land-time `_refuse_anchor_terminal_land` guard that unconditionally
refuses landing an anchor=True ticket to done/dropped.

Two pieces remain, out of T-1856's declared scope
(src/frob/tickets/_models.py, src/frob/tickets/_land.py only):

1. CLI wiring: `frob ticket anchor <id> --set/--clear --reason TEXT`,
   needs src/frob/app/ticket_runner/_mutate.py (the `_scope`/`_scope_ack`
   command-family module) plus src/frob/_cli_parsers/_ticket/_metadata.py
   (the argparse registration) plus the CLI_WIRING_FILES trio
   (src/frob/__main__.py, src/frob/app/config.py,
   src/frob/app/ticket_runner/__init__.py). Today `set_anchor` is
   library-only; a coordinator/agent must call it via
   `uv run python -c "from frob.tickets._land import set_anchor; ..."`
   or a REPL, not a first-class command.

2. `frob ticket doable` output disclosure: an anchor ticket should be
   marked/annotated in `doable`'s listing (so it reads as "intentionally
   permanent," not "stale/forgotten"). Needs
   src/frob/tickets/_doable.py and/or
   src/frob/app/ticket_runner/_query.py's `_doable`/`_render_doable_
   show_blocked` -- both were explicitly off-limits for this session
   (another agent held _doable.py).

T-1820 and T-1831 (the live anchor-ticket examples cited in T-1853's
body) should have `set_anchor(root, id, anchor=True, reason=...)` run
against them once the CLI lands, so the marker is actually set on the
real anchors this ticket exists to protect -- today it exists as a
mechanism but is not yet applied to either.
