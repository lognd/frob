---
id: T-1975
title: Wire frob ticket scope --demote-to-evidence-only to T-1944's demote_to_evidence_only
state: queued
kind: feature
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/_cli_parsers/_ticket/_metadata.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Follow-up from T-1944 (evidence-only scope): `frob.tickets.demote_to_
evidence_only` exists and is tested, but there is no CLI surface for it
yet -- an operator/agent unblocking a T-1686-shaped stuck ticket today
has to call the library function directly rather than run a `frob
ticket scope` subcommand. Wire `frob ticket scope <id> --demote-to-
evidence-only GLOB... --reason TEXT` (or a dedicated verb, whichever
matches this repo's existing `scope`/`scope-ack` CLI convention more
closely) through `src/frob/_cli_parsers/_ticket/`.

Left out of T-1944's own scope (declared `src/frob/tickets/`) because
the CLI parser tree lives outside that path.
