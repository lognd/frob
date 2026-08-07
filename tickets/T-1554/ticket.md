---
id: T-1554
title: 'land: design the remaining post-commit checkpoint gap beyond the sweep window
  (T-1523 follow-up)'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1523 closed a narrow slice of this (the post-land unscoped-error sweep's
own killable window, via a durable marker + read-only reconciliation on
the next invocation). Two larger design questions from its body remain
open:

- Option A (full): make EVERY intermediate land state durable/self-
  describing, not just the sweep window, so a kill at ANY instant is
  recoverable, including push and --finish's own worktree-removal step
  (currently believed safe/idempotent per playbook section 0 item 9 and
  T-1175's LAND-PROOF, but never load-bearing-verified against a real
  SIGTERM injection the way T-1523's own test suite does for the sweep).
- Option B: a separately-invocable `frob ticket land --verify-only <sha>`
  resumable CLI step, decoupled from a fresh merge/commit entirely.

Needs its own design doc before implementation, same as T-1523's body
said before it was scoped down.