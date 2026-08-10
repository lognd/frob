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

## Done report

Added a `runs_last: bool` marker (T-1613) to `Ticket`/`TicketSpec` that keeps
a ticket structurally undoable while any other ticket is open -- not merely
advisory (the scope-ack/TICK009 failure mode).

Definition chosen for "any other ticket open": every OTHER ticket, excluding
fellow runs-last tickets, whose state is non-terminal
(queued/planned/in-progress/blocked -- the same `_OPEN_STATES` set
`blocked_by` already uses). This was the strict choice over "only
in-progress with a live lease": a queued ticket someone starts a minute
later is the identical hazard, just deferred, so gating on in-progress alone
would leave the exact dispatch-into-the-window gap the marker exists to
close. Fellow runs-last tickets are excluded from the count so two or more
can coexist and order among themselves via ordinary `blocked_by`, per the
ticket's own requirement.

Enforcement, two structural points (never a warning-only nudge):
- `doable` (`frob.tickets._doable._doable_candidates`, new
  `_other_open_tickets` helper): a runs-last candidate never surfaces while
  the check above is non-empty.
- `start` (`frob.tickets._evidence._transition_guard`'s IN_PROGRESS branch,
  new `_runs_last_start_blockers`): the transition refuses with a new
  `TicketError.RunsLastBlocked`, and the log line names every remaining
  open ticket id.

Filing-invalidation warning (the requirement that makes this real rather
than cosmetic): `frob.tickets._new_renumber.new_ticket` now calls
`_warn_if_runs_last_ticket_in_progress` before every fresh ORDINARY
(non-runs-last) ticket is filed -- logs a loud WARNING naming every
IN_PROGRESS runs-last ticket, does not block filing.

CLI surface: `frob ticket runs-last <id> <on|off>` (new `set_runs_last`
setter mirroring `set_tier`), wired through the full parser tree
(`_cli_parsers/_ticket/_metadata.py` + `__init__.py`), `AppConfig`
(`app/config.py` + the `_config_external.py` string-field allowlist --
confirmed by direct repro that omitting the allowlist entry means argparse
parses the value but `AppConfig` never receives it), and the dispatch table
(`app/ticket_runner/_mutate.py::_runs_last` + `app/ticket_runner/__init__.py`).
Did not wire a `--runs-last` flag onto `frob ticket new` itself (kept the
surface to the minimum needed to verify the mechanism end to end) --
setting it via `runs-last <id> on` immediately after filing is the current
path; a `new --runs-last` convenience flag is a natural, small follow-up if
wanted.

Verified end-to-end by hand in a scratch repo (not just unit tests): filed
a runs-last ticket, filed an ordinary ticket, confirmed `doable`/`start`
both refuse the runs-last ticket, dropped the ordinary ticket, confirmed
`doable`/`start` succeed once it was the only open ticket, started the
runs-last ticket, filed a fresh ordinary ticket, confirmed the WARNING
fires naming the running ticket id, and confirmed two runs-last tickets
coexist and both surface in `doable`.

Scope grew substantially past the narrowed dispatch scope (which covered
only `_models.py`/`_store.py`/query-side files) because the actual
enforcement points live in `_doable.py` (doable filtering) and
`_evidence.py` (start-time transition guard), neither of which were in the
original grant; extended with `--reason` file by file as each dependency
surfaced (`_doable.py`, `_evidence.py`, `_new_renumber.py`, `_setters.py`,
`_cli_parsers/_ticket/_metadata.py` and its `__init__.py`,
`app/ticket_runner/_mutate.py`, `app/_config_external.py`,
`docs/modules/tickets.md`, `design/frob.strata`, and this ticket's own v2
ledger file `tickets/T-1613/ticket.md`, which SCOPE001 flagged as outside
scope despite `LEDGER_PATH`'s always-implicit rule only covering the
legacy single-file `tickets.md` path, not this checkout's v2 per-ticket
layout). Landed as one ticket per the "propose a split only if it turns
out larger" instruction -- the mechanism is cohesive (one field, two
enforcement points, one warning, one CLI verb) and none of it works
half-landed.

`frob check --only prework --only scope --only sys --ticket T-1613` is
clean (PRE001/SCOPE001/SELFAUDIT001 all resolved). `frob fmt --check`
found the repo's pre-existing 51-file litmus/`.strata` reformatting debt,
unrelated to this ticket; the one file this ticket actually touched that
needed reformatting (`_setters.py`) is now clean.

### Changed
```
 tickets/T-1613/done-report.md |  94 ++++++++++++++++++++++++++++
 tickets/T-1613/ticket.md      | 139 +++++++++++++++++++++++++++++++++++++++++-
 2 files changed, 232 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_organization.py::TestRunsLast::test_set_runs_last_updates_field` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestRunsLast::test_doable_excludes_runs_last_while_other_ticket_open` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestRunsLast::test_doable_includes_runs_last_once_all_other_tickets_terminal` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestRunsLast::test_start_refuses_runs_last_while_other_ticket_open` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestRunsLast::test_multiple_runs_last_tickets_do_not_block_each_other` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestRunsLast::test_filing_new_ticket_while_runs_last_in_progress_warns` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 1176 warning(s), 723 waived
- error-findings: none (measured, zero errors)
