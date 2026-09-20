---
id: T-3613
title: make land --queue/--drain (T-1444) the default agent path with pollable completion
  records
state: done
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
- tests/unit/test_land_default_queue.py
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
- op: add
  glob: src/frob/app/_config_external.py
  reason: wire land_default through [tool.frob] table
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/unit/test_land_default_queue.py
  reason: unit tests for auto-queue default + --status cmd
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
evidence:
- tests/unit/test_land_default_queue.py::TestApplyLandDefaultQueue::test_frob_agent_env_promotes_to_queue
- tests/unit/test_land_default_queue.py::TestLandStatusCmd::test_status_prints_queued_record
- tests/unit/test_land_queue.py::TestIntentRecord::test_enqueue_writes_a_readable_intent_record
- tests/unit/test_land_queue.py::TestDrainNext::test_dead_drainer_landing_entry_is_reclaimed_and_redrained
- tests/unit/test_land_queue.py::TestDrainNext::test_live_drainer_landing_entry_is_not_reclaimed
- tests/unit/test_land_default_queue.py::TestApplyLandDefaultQueue::test_neither_signal_keeps_synchronous_default
- tests/unit/test_land_queue.py::TestEnqueue::test_enqueue_returns_queued_entry
designated_repro_test: null
acceptance:
- text: frob ticket land <id> under FROB_AGENT (or [tool.frob] land_default="queue")
    ENQUEUES and returns in seconds with the intent recorded, and one drainer process
    does the serial work
  evidence:
  - tests/unit/test_land_default_queue.py::TestApplyLandDefaultQueue::test_frob_agent_env_promotes_to_queue
- text: a per-intent completion record file under .frob/land-queue/<ticket>.json (state
    queued/landing/landed/failed, refusal text verbatim, commit sha) that agents poll
    cheaply, plus frob ticket land --status <id> printing it
  evidence:
  - tests/unit/test_land_default_queue.py::TestLandStatusCmd::test_status_prints_queued_record
  - tests/unit/test_land_queue.py::TestIntentRecord::test_enqueue_writes_a_readable_intent_record
- text: 'drainer crash recovery: the queue file survives, the next --drain picks up,
    a dead drainer''s landing entry is reclaimed via pid liveness (reusing the existing
    land.lock reclaim logic''s posture)'
  evidence:
  - tests/unit/test_land_queue.py::TestDrainNext::test_dead_drainer_landing_entry_is_reclaimed_and_redrained
  - tests/unit/test_land_queue.py::TestDrainNext::test_live_drainer_landing_entry_is_not_reclaimed
- text: docs section and tests per acceptance criterion
  evidence:
  - tests/unit/test_land_default_queue.py::TestApplyLandDefaultQueue::test_neither_signal_keeps_synchronous_default
  - tests/unit/test_land_queue.py::TestEnqueue::test_enqueue_returns_queued_entry
acceptance_amendments:
- op: remove
  index: 8
  old_text: docs section and tests per acceptance criterion
  new_text: null
  reason: duplicate from a killed-then-retried accept call
  actor: logan
  at: '2026-09-16'
- op: remove
  index: 7
  old_text: 'drainer crash recovery: the queue file survives, the next --drain picks
    up, a dead drainer''s landing entry is reclaimed via pid liveness (reusing the
    existing land.lock reclaim logic''s posture)'
  new_text: null
  reason: duplicate from a killed-then-retried accept call
  actor: logan
  at: '2026-09-16'
- op: remove
  index: 6
  old_text: a per-intent completion record file under .frob/land-queue/<ticket>.json
    (state queued/landing/landed/failed, refusal text verbatim, commit sha) that agents
    poll cheaply, plus frob ticket land --status <id> printing it
  new_text: null
  reason: duplicate from a killed-then-retried accept call
  actor: logan
  at: '2026-09-16'
- op: remove
  index: 5
  old_text: frob ticket land <id> under FROB_AGENT (or [tool.frob] land_default="queue")
    ENQUEUES and returns in seconds with the intent recorded, and one drainer process
    does the serial work
  new_text: null
  reason: duplicate from a killed-then-retried accept call
  actor: logan
  at: '2026-09-16'
- op: remove
  index: 5
  old_text: placeholder-resync-trigger
  new_text: null
  reason: remove resync-trigger placeholder criterion
  actor: logan
  at: '2026-09-16'
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