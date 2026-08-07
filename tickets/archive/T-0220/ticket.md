---
id: T-0220
title: 'T-0176 scope gap: src/frob/__main__.py missing from declared scope'
state: done
kind: docs
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:grep -n 'frob:waive SCOPE001 reason="T-0176 scope omitted this file, filed T-0220"'
  src/frob/__main__.py exit=0 sha256=5215691879a9
designated_repro_test: null
threat: null
component: null
---
T-0176's scope listed src/frob/tickets/**, src/frob/app/**, tests/**, docs/modules/tickets.md, tickets.md but omitted src/frob/__main__.py -- every prior ticket-subcommand-adding ticket (e.g. T-0162) explicitly included src/frob/__main__.py in scope, since the ticket subcommand argparse wiring lives there, not under src/frob/app/. T-0176 needed exactly that (frob ticket land's --worktree/--dry-run argparse registration) and could not deliver a usable CLI command without it. Waived SCOPE001 at src/frob/__main__.py in T-0176's commit rather than expanding scope unilaterally; this ticket exists to note the gap for future ticket-scope authoring (mechanically: any ticket adding a new frob subcommand should include src/frob/__main__.py in scope up front).