---
id: T-1613
title: 'frob cannot express runs-last: add a marker that stays undoable while any
  other ticket is open'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_models.py
- src/frob/tickets/_store.py
- src/frob/app/ticket_runner/_query.py
- src/frob/_cli_parsers/_ticket/_query.py
- tests/test_tickets_organization.py
- docs/modules/cli.md
- src/frob/tickets/_doable.py
- src/frob/tickets/_evidence.py
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_setters.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/tickets/__init__.py
- src/frob/_cli_parsers/_ticket/__init__.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/_config_external.py
- docs/modules/tickets.md
- tickets/T-1613/ticket.md
- design/frob.strata
- tickets/T-1613/done-report.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/**
  reason: 'TICK009: narrowing my own over-broad filing-time scope to the files this
    ticket actually names'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_models.py
  reason: narrowed from a package glob to the specific modules named in the ticket
    body
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_store.py
  reason: narrowed from a package glob to the specific modules named in the ticket
    body
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: docs/**
  reason: 'TICK009 pre-dispatch narrowing: four mega-globs replaced with the real
    surface for a runs-last marker'
  actor: logan
  at: '2026-08-07'
- op: remove
  glob: tests/**
  reason: 'TICK009 pre-dispatch narrowing: four mega-globs replaced with the real
    surface for a runs-last marker'
  actor: logan
  at: '2026-08-07'
- op: remove
  glob: src/frob/app/ticket_runner/**
  reason: 'TICK009 pre-dispatch narrowing: four mega-globs replaced with the real
    surface for a runs-last marker'
  actor: logan
  at: '2026-08-07'
- op: remove
  glob: src/frob/_cli_parsers/**
  reason: 'TICK009 pre-dispatch narrowing: four mega-globs replaced with the real
    surface for a runs-last marker'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: 'TICK009 pre-dispatch narrowing: four mega-globs replaced with the real
    surface for a runs-last marker'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_query.py
  reason: 'TICK009 pre-dispatch narrowing: four mega-globs replaced with the real
    surface for a runs-last marker'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_tickets_organization.py
  reason: 'TICK009 pre-dispatch narrowing: four mega-globs replaced with the real
    surface for a runs-last marker'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/cli.md
  reason: 'TICK009 pre-dispatch narrowing: four mega-globs replaced with the real
    surface for a runs-last marker'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/tickets/_doable.py
  reason: runs-last enforcement lives in doable filtering (_doable.py) and start-time
    transition guard (_evidence.py); filing-warning belongs in ticket creation (_new_renumber.py);
    a settable marker needs a setter (_setters.py) and its CLI registration (_cli_parsers/_ticket/_metadata.py),
    mirroring the existing set_tier/frob-ticket-tier pattern -- app/ticket_runner/**
    is already implicitly in scope for a FEATURE ticket per CLI_WIRING_FILES
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: runs-last enforcement lives in doable filtering (_doable.py) and start-time
    transition guard (_evidence.py); filing-warning belongs in ticket creation (_new_renumber.py);
    a settable marker needs a setter (_setters.py) and its CLI registration (_cli_parsers/_ticket/_metadata.py),
    mirroring the existing set_tier/frob-ticket-tier pattern -- app/ticket_runner/**
    is already implicitly in scope for a FEATURE ticket per CLI_WIRING_FILES
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: runs-last enforcement lives in doable filtering (_doable.py) and start-time
    transition guard (_evidence.py); filing-warning belongs in ticket creation (_new_renumber.py);
    a settable marker needs a setter (_setters.py) and its CLI registration (_cli_parsers/_ticket/_metadata.py),
    mirroring the existing set_tier/frob-ticket-tier pattern -- app/ticket_runner/**
    is already implicitly in scope for a FEATURE ticket per CLI_WIRING_FILES
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/tickets/_setters.py
  reason: runs-last enforcement lives in doable filtering (_doable.py) and start-time
    transition guard (_evidence.py); filing-warning belongs in ticket creation (_new_renumber.py);
    a settable marker needs a setter (_setters.py) and its CLI registration (_cli_parsers/_ticket/_metadata.py),
    mirroring the existing set_tier/frob-ticket-tier pattern -- app/ticket_runner/**
    is already implicitly in scope for a FEATURE ticket per CLI_WIRING_FILES
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: runs-last enforcement lives in doable filtering (_doable.py) and start-time
    transition guard (_evidence.py); filing-warning belongs in ticket creation (_new_renumber.py);
    a settable marker needs a setter (_setters.py) and its CLI registration (_cli_parsers/_ticket/_metadata.py),
    mirroring the existing set_tier/frob-ticket-tier pattern -- app/ticket_runner/**
    is already implicitly in scope for a FEATURE ticket per CLI_WIRING_FILES
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: runs-last enforcement in _doable.py/_evidence.py/_new_renumber.py/_setters.py
    late-imports shared helpers (_OPEN_STATES, _load_ticket_and_queue) from this module,
    per existing scope-closure warnings
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/_cli_parsers/_ticket/__init__.py
  reason: wiring the new runs-last CLI verb requires registering its parser in the
    _ticket parser-tree __init__ and its handler in app/ticket_runner/_mutate.py (mirrors
    set_tier/_tier); --runs-last on frob ticket new needs app/ticket_runner/_new.py's
    TicketSpec construction
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: wiring the new runs-last CLI verb requires registering its parser in the
    _ticket parser-tree __init__ and its handler in app/ticket_runner/_mutate.py (mirrors
    set_tier/_tier); --runs-last on frob ticket new needs app/ticket_runner/_new.py's
    TicketSpec construction
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: wiring the new runs-last CLI verb requires registering its parser in the
    _ticket parser-tree __init__ and its handler in app/ticket_runner/_mutate.py (mirrors
    set_tier/_tier); --runs-last on frob ticket new needs app/ticket_runner/_new.py's
    TicketSpec construction
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'the string-field allowlist frob ticket new/tier''s own values flow through
    (_build_external_config_kwargs) must list ticket_runs_last_value too, or argparse
    parses it but AppConfig never receives it -- confirmed by manual repro: frob ticket
    runs-last T-0001 on failed with ''requires <id> <on|off>'' despite both positionals
    parsing fine'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/tickets.md
  reason: T-1613's own doc home (Public API describes blocks + a new Runs-last marker
    section) needed edits explaining the mechanism -- docs/modules/cli.md alone (originally
    scoped) covers only the generated top-level command table, not the ticket-subcommand
    narrative docs
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1613/ticket.md
  reason: v2 store mode's per-ticket ledger file for T-1613 itself -- LEDGER_PATH's
    always-in-scope rule only covers the legacy single tickets.md path, not the v2
    per-ticket file this checkout is actually using; needed so recording the sweep/evidence/Done-report
    against this ticket's own record does not itself trip SCOPE001
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: 'SELFAUDIT001/SYS104: the tickets_ledger design node''s public-symbol interface
    list must declare set_runs_last (new public export) or self-audit flags it as
    imported-but-undeclared'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1613/done-report.md
  reason: same v2-store per-ticket-file gap as tickets/T-1613/ticket.md -- the Done
    report the CLI itself writes for this ticket lives at this path in v2 mode and
    SCOPE001 flags it the same way
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_tickets_organization.py::TestRunsLast::test_set_runs_last_updates_field
- tests/test_tickets_organization.py::TestRunsLast::test_doable_excludes_runs_last_while_other_ticket_open
- tests/test_tickets_organization.py::TestRunsLast::test_doable_includes_runs_last_once_all_other_tickets_terminal
- tests/test_tickets_organization.py::TestRunsLast::test_start_refuses_runs_last_while_other_ticket_open
- tests/test_tickets_organization.py::TestRunsLast::test_multiple_runs_last_tickets_do_not_block_each_other
- tests/test_tickets_organization.py::TestRunsLast::test_filing_new_ticket_while_runs_last_in_progress_warns
designated_repro_test: null
threat: null
component: null
---
frob can express "this ticket is blocked by that ticket" but cannot express "this ticket must be the last thing done in the repository". The distinction matters for audit-shaped work whose correctness depends on everything else being finished.

Concrete case: the waiver cop-out audit. Its blocked_by edges can only name tickets that existed when it was filed. Any ticket filed afterwards must ALSO precede it, but nothing in the graph says so, and nothing stops an agent from popping it early. Today the constraint survives only as prose in the body, which is exactly the kind of tribal knowledge frob exists to replace with enforcement.

Proposed: a runs-last marker (a tier value, a flag, or a blocked_by_all sentinel) that makes such a ticket structurally undoable while ANY other non-terminal ticket exists.

Requirements:
- `frob ticket doable` must never return a runs-last ticket while any other queued/in-progress ticket exists, regardless of filing order.
- `frob ticket start` on one must refuse with a message naming what remains.
- More than one runs-last ticket must be allowed (they order among themselves by ordinary blocked_by edges).
- Filing a NEW ordinary ticket while a runs-last ticket is in-progress should warn loudly: the precondition it started under has been invalidated.

That last requirement is the one that makes this real rather than cosmetic -- the failure mode is not starting the audit too early, it is finishing it and then having new work land that silently invalidates its conclusions.