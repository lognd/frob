---
id: T-2574
title: 'M1: Ticket.milestone field, semver ordering, CLI surface'
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: high
parent: T-2573
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_models.py
- src/frob/tickets/_setters.py
- src/frob/tickets/_new_renumber.py
- src/frob/app/ticket_runner/_mutate.py
- docs/modules/tickets-data-storage.md
- src/frob/_cli_parsers/_ticket/_new.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/_cli_parsers/_ticket/__init__.py
- src/frob/app/_config_external.py
- src/frob/tickets/__init__.py
- src/frob/app/ticket_runner/_new.py
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/semver.py
  reason: 'corrected scope: semver.py and cli/tickets.py do not exist; new_ticket
    lives in _new_renumber.py, CLI wiring for set_runs_last-style setters lives in
    app/ticket_runner/_mutate.py'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: src/frob/cli/tickets.py
  reason: 'corrected scope: semver.py and cli/tickets.py do not exist; new_ticket
    lives in _new_renumber.py, CLI wiring for set_runs_last-style setters lives in
    app/ticket_runner/_mutate.py'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: 'corrected scope: semver.py and cli/tickets.py do not exist; new_ticket
    lives in _new_renumber.py, CLI wiring for set_runs_last-style setters lives in
    app/ticket_runner/_mutate.py'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: 'corrected scope: semver.py and cli/tickets.py do not exist; new_ticket
    lives in _new_renumber.py, CLI wiring for set_runs_last-style setters lives in
    app/ticket_runner/_mutate.py'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: src/frob/tickets/_filing.py
  reason: removed nonexistent _filing.py; added the doc that must gain the milestone
    field/setter/CLI doc closure
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: removed nonexistent _filing.py; added the doc that must gain the milestone
    field/setter/CLI doc closure
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_new.py
  reason: T-0446/T-1848 CLI-wiring grant covers __main__.py/app/config.py/ticket_runner/__init__.py
    but the actual argparse flag definitions for --milestone and the milestone mutate
    verb live in _cli_parsers/_ticket/_new.py and _metadata.py (plus __init__.py's
    registration list), and the argparse-Namespace-to-kwargs copy lives in _config_external.py;
    without these the CLI surface the ticket requires cannot be wired at all
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: T-0446/T-1848 CLI-wiring grant covers __main__.py/app/config.py/ticket_runner/__init__.py
    but the actual argparse flag definitions for --milestone and the milestone mutate
    verb live in _cli_parsers/_ticket/_new.py and _metadata.py (plus __init__.py's
    registration list), and the argparse-Namespace-to-kwargs copy lives in _config_external.py;
    without these the CLI surface the ticket requires cannot be wired at all
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/_cli_parsers/_ticket/__init__.py
  reason: T-0446/T-1848 CLI-wiring grant covers __main__.py/app/config.py/ticket_runner/__init__.py
    but the actual argparse flag definitions for --milestone and the milestone mutate
    verb live in _cli_parsers/_ticket/_new.py and _metadata.py (plus __init__.py's
    registration list), and the argparse-Namespace-to-kwargs copy lives in _config_external.py;
    without these the CLI surface the ticket requires cannot be wired at all
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/_config_external.py
  reason: T-0446/T-1848 CLI-wiring grant covers __main__.py/app/config.py/ticket_runner/__init__.py
    but the actual argparse flag definitions for --milestone and the milestone mutate
    verb live in _cli_parsers/_ticket/_new.py and _metadata.py (plus __init__.py's
    registration list), and the argparse-Namespace-to-kwargs copy lives in _config_external.py;
    without these the CLI surface the ticket requires cannot be wired at all
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: set_runs_last is re-exported from frob.tickets.__init__ for _mutate.py's
    import; set_milestone needs the same re-export or the CLI wiring cannot import
    it
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: set_runs_last is re-exported from frob.tickets.__init__ for _mutate.py's
    import; set_milestone needs the same re-export or the CLI wiring cannot import
    it
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: TicketSpec construction for 'frob ticket new' lives here (_resolve_new_ticket_spec);
    needed to wire cfg.ticket_milestone into TicketSpec(milestone=...), the --milestone
    flag's actual effect
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_tickets.py
  reason: unit tests for validate_milestone/set_milestone/TicketSpec.milestone need
    to live where existing sibling Ticket-model tests already live (T-0838's TestUnknownFieldForwardCompat
    precedent), so evidence and the file write are both accounted for
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_tickets.py::TestValidateMilestone::test_valid_semver_accepted
- tests/test_tickets.py::TestValidateMilestone::test_invalid_string_refused
- tests/test_tickets.py::TestValidateMilestone::test_ordering_is_numeric_not_lexical
- tests/test_tickets.py::TestSetMilestone::test_valid_semver_sets_field
- tests/test_tickets.py::TestSetMilestone::test_invalid_semver_refused
- tests/test_tickets.py::TestNewTicketMilestone::test_new_ticket_with_valid_milestone
- tests/test_tickets.py::TestNewTicketMilestone::test_new_ticket_with_invalid_milestone_refused
- tests/test_tickets.py::TestNewTicketMilestone::test_new_ticket_without_milestone_is_unmilestoned
designated_repro_test: null
acceptance:
- text: Ticket.milestone/TicketSpec.milestone exist, extra=allow preserved, invalid
    semver refused at write time, and semver ordering is real (1.10.0 > 1.9.0)
  evidence:
  - tests/test_tickets.py::TestValidateMilestone::test_valid_semver_accepted
  - tests/test_tickets.py::TestValidateMilestone::test_invalid_string_refused
  - tests/test_tickets.py::TestValidateMilestone::test_ordering_is_numeric_not_lexical
  - tests/test_tickets.py::TestSetMilestone::test_valid_semver_sets_field
  - tests/test_tickets.py::TestSetMilestone::test_invalid_semver_refused
- text: frob ticket milestone <id> <value> and --milestone on frob ticket new both
    work end to end
  evidence:
  - tests/test_tickets.py::TestNewTicketMilestone::test_new_ticket_with_valid_milestone
  - tests/test_tickets.py::TestNewTicketMilestone::test_new_ticket_with_invalid_milestone_refused
  - tests/test_tickets.py::TestNewTicketMilestone::test_new_ticket_without_milestone_is_unmilestoned
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: e4b469d05937aa96ecf2fec98b8a2e4e642ba449
---
Add `milestone: str | None = None` to `Ticket` (src/frob/tickets/_models.py)
and the filing spec, plus a total order over milestone values via semver
comparison. Invalid milestone strings must be REFUSED at write time with a
clear error, not sorted arbitrarily at read time. Semver comparison must be
a real ordered comparison, not a string compare: "1.10.0" > "1.9.0" must
hold.

CLI surface:
- `frob ticket milestone <id> <value>` -- mirror `set_runs_last` in
  src/frob/tickets/_setters.py (same validate-then-write shape, same
  ledger-commit path).
- `--milestone` flag on `frob ticket new`.

Scope must stay narrow: model field + semver comparator + setter + CLI
parser wiring only. Explicitly OUT of scope: no changes to
_doable_candidates, _doable_sort_key, MILE00x gates, or REL001 -- those
are M2 through M6.

Milestone NEVER blocks on its own -- it ORDERS, nothing more, at this
stage. An unmilestoned OPEN ticket is fine for M1 (MILE003 in M2 is what
enforces the field is set). extra="allow" on Ticket (confirmed:
src/frob/tickets/_models.py, ConfigDict(frozen=True, extra="allow")) means
this field is safely additive -- no ledger migration needed.