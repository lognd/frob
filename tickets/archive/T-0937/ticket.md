---
id: T-0937
title: 'ticket organization CLI surface: tier/sprint flags, sprint assign/show, doable
  --by-parent/--sprint'
state: dropped
kind: feature
origin: human
created: '2026-07-26'
priority: medium
parent: T-0715
tier: ticket
sprint: null
scope:
- src/frob/__main__.py
- src/frob/app/config.py
- src/frob/app/ticket_runner.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-0715 filed the `TicketTier` field (epic|story|ticket) plus its two
structural rules (doable leaf-only, close-blocks-on-open-descendant) and
the `sprint` field, all in `src/frob/tickets/**`. It deliberately did NOT
wire a CLI surface for either, because that needs files outside T-0715's
declared scope:

- `frob ticket new --tier epic|story|ticket` / `--sprint LABEL`
- `frob ticket sprint assign <id> <label>`
- `frob ticket sprint show <label>` (committed tickets, state rollup,
  closed-count velocity)
- `frob ticket doable --sprint LABEL` (restrict the queue to a commitment)
- `frob ticket doable --by-parent` (group a story's remaining leaves
  together, the user's "pop-the-whole-stack" concern)

argparse wiring for new flags/subcommands lives in `src/frob/__main__.py`
and new `AppConfig` fields live in `src/frob/app/config.py` -- both
outside T-0715's `scope` (`src/frob/tickets/**`,
`src/frob/app/ticket_runner.py`, `docs/modules/tickets.md`). This ticket's
scope should include those two files plus `src/frob/app/ticket_runner.py`
(already open) so the handlers can actually be dispatched to.

Acceptance: GIVEN a ticket with tier=story and sprint=sprint-1 WHEN `frob
ticket new --tier story --sprint sprint-1` is used THEN the created ticket
carries both fields; GIVEN tickets assigned to sprint-1 WHEN `frob ticket
sprint show sprint-1` runs THEN it lists committed tickets with a state
rollup and a closed-count velocity number; GIVEN a story with several open
leaf children WHEN `frob ticket doable --by-parent` runs THEN the leaves
group under their story instead of a single flat list.

## Drop reason
- 2026-07-27: folded into T-0715 (absorbed by T-0715)