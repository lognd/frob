---
id: T-2310
title: rapid profile needs a real verification-debt drain mechanism (design decision
  deferred from T-2290)
state: done
kind: feature
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/verify/**
- src/frob/app/verify_runner.py
- src/frob/_cli_parsers/_verify.py
- docs/modules/tickets-verify-sweep.md
evidence_scope:
- tests/unit/verify/test_drain.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/verify_runner.py
  reason: T-2310 drain needs CLI wiring (verify_runner.py handler + _cli_parsers/_verify.py
    subparser) and a doc anchor for the new public symbols; _land_cmd.py excluded
    -- live lease held by T-2303
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/_cli_parsers/_verify.py
  reason: T-2310 drain needs CLI wiring (verify_runner.py handler + _cli_parsers/_verify.py
    subparser) and a doc anchor for the new public symbols; _land_cmd.py excluded
    -- live lease held by T-2303
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: T-2310 drain needs CLI wiring (verify_runner.py handler + _cli_parsers/_verify.py
    subparser) and a doc anchor for the new public symbols; _land_cmd.py excluded
    -- live lease held by T-2303
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/verify/test_drain.py::TestRunDrainAsync::test_declines_while_a_land_is_in_progress
- tests/unit/verify/test_drain.py::TestRunDrainAsync::test_never_blocks_or_loops_over_the_backlog
- tests/unit/verify/test_drain.py::TestSpawnDeferredDrain::test_spawns_a_detached_child
- tests/unit/verify/test_drain.py::TestSpawnDeferredDrain::test_exec_disabled_refuses_without_spawning
- tests/unit/verify/test_drain.py::TestDrainAdvancesWatermarkEndToEnd::test_green_round_advances_watermark_a_subsequent_round_sees
- tests/unit/verify/test_drain.py::TestDrainAdvancesWatermarkEndToEnd::test_unmeasurable_round_leaves_watermark_untouched_not_corrupt
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2290 fixed (c) the unverified-depth/commits-since-watermark reconciliation
and (b) a soft, non-blocking rapid-profile warning once verification debt
crosses a threshold (frob.verify._backpressure.rapid_soft_warning), but
explicitly did NOT implement direction (a): an actual drain mechanism
that advances the watermark on a cadence independent of a land (idle-time
sweep, explicit `frob verify drain`, or a coordinator-invoked catch-up).

Right now the warning this ticket added has nowhere to point an operator
except "run `frob verify now` by hand" -- which requires an operator to
notice the warning AND remember the command exists (the standing
"automatic over commands" directive this repo already holds: a command
requires knowledge of the command). Without a real drain, a rapid-profile
repo can accumulate unbounded verification debt forever, loudly warned
about but never actually resolved automatically.

This needs a design decision (which of the three drain shapes, and how it
interacts with the existing coalescing worker in frob.verify._worker) that
T-2290's own dispatch explicitly deferred rather than guessed at.