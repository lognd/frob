---
id: T-3613
title: make land --queue/--drain (T-1444) the default agent path with pollable completion
  records
state: in-progress
kind: ux
origin: human
created: '2026-08-31'
priority: medium
parent: T-3611
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: 0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_queue.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/_cli_parsers/_ticket/_closeout.py
- docs/modules/tickets-verify-sweep.md
- tests/unit/test_land_queue.py
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
- docs/modules/tickets-landing.md
- src/frob/_cli_parsers/_ticket/_progress.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/tickets/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_queue.py
  reason: queue/drain implementation
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: --queue/--drain CLI wiring, land default path
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: queue/drain default land path + docs/tests
  actor: logan
  at: '2026-09-16'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: queue/drain default land path + docs/tests
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/unit/test_land_queue.py
  reason: queue/drain default land path + docs/tests
  actor: logan
  at: '2026-09-16'
- op: add
  glob: design/frob.strata
  reason: queue/drain default land path + docs/tests
  actor: logan
  at: '2026-09-16'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: queue/drain default land path + docs/tests
  actor: logan
  at: '2026-09-16'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: land default path doc update
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_progress.py
  reason: actual home of --queue/--drain flags, need --status
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/app/config.py
  reason: land_default config field
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/app/_config_external.py
  reason: wire land_default through [tool.frob] table
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/app/_config_external.py
  reason: wire land_default through [tool.frob] table
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/app/_config_external.py
  reason: wire land_default through [tool.frob] table
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/app/_config_external.py
  reason: wire land_default through [tool.frob] table
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/app/_config_external.py
  reason: wire land_default through [tool.frob] table
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/app/_config_external.py
  reason: wire land_default through [tool.frob] table
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/app/_config_external.py
  reason: wire land_default through [tool.frob] table
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/app/_config_external.py
  reason: wire land_default through [tool.frob] table
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: export read_intent_record alongside existing queue exports
  actor: logan
  at: '2026-09-16'
triage_changes:
- field: priority
  old_value: high
  new_value: medium
  reason: 'T-4483 follow-up: TICK004 escalated to error on 2026-09-15 (15d queued
    > 2x the 7d high threshold) and reds every CI leg; these are T-3611 latency-epic
    children, sprint v0.532.0 work behind the v0.531.0 alpha cut, not alpha-path work,
    so medium is the honest priority'
  actor: logan
  at: '2026-09-14'
- field: sprint
  old_value: null
  new_value: v0.532.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-15'
- field: milestone
  old_value: null
  new_value: 0.532.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-15'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
src/frob/tickets/_land_queue.py already implements a land queue/drain
design (one drainer, losers enqueue). Verify the CLI surface
(--queue/--drain/--plan flags), fix whatever keeps agents from using
it, and make ENQUEUE the documented default agent path: an
implementer's land call should return in seconds (intent recorded) with
the single drainer doing the serial work, instead of every agent
parking in a 60s sleep loop re-probing land.lock. Include: drainer
crash recovery (queue survives, next drainer picks up), loud per-intent
completion records agents can poll cheaply (a file, not a lock probe),
and the tickets-landing doc updated. Measure: agent wall-time from
"done implementing" to "shell free" drops from minutes/hours to
seconds; drain throughput unchanged or better.
