---
id: T-2569
title: ticket close reports an UNMEASURABLE evidence batch as evidence no longer passes
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_land.py
- tests/test_ticket_reverify.py
- tests/test_tickets_acceptance.py
- tests/test_tickets_evidence_cli.py
- tests/unit/test_app_runners_batch7.py
- tests/unit/test_ticket_runner_designate_repro.py
- tests/unit/test_ticket_runner_land_release.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: 'T-2569: thread SpawnFailed/timeout as UNMEASURED instead of FAILED through
    _verify_ids_passing and its close/land consumers'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/_close_cmd.py
  reason: 'T-2569: thread SpawnFailed/timeout as UNMEASURED instead of FAILED through
    _verify_ids_passing and its close/land consumers'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'T-2569: thread SpawnFailed/timeout as UNMEASURED instead of FAILED through
    _verify_ids_passing and its close/land consumers'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'T-2569: update mocks of _verify_ids_passing (frozenset->dict[str,VerifyOutcome])
    and add UNMEASURED/FAILED positive-control tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_ticket_reverify.py
  reason: 'T-2569: update mocks of _verify_ids_passing (frozenset->dict[str,VerifyOutcome])
    and add UNMEASURED/FAILED positive-control tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_tickets_acceptance.py
  reason: 'T-2569: update mocks of _verify_ids_passing (frozenset->dict[str,VerifyOutcome])
    and add UNMEASURED/FAILED positive-control tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_tickets_evidence_cli.py
  reason: 'T-2569: update mocks of _verify_ids_passing (frozenset->dict[str,VerifyOutcome])
    and add UNMEASURED/FAILED positive-control tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: 'T-2569: update mocks of _verify_ids_passing (frozenset->dict[str,VerifyOutcome])
    and add UNMEASURED/FAILED positive-control tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_ticket_runner_designate_repro.py
  reason: 'T-2569: update mocks of _verify_ids_passing (frozenset->dict[str,VerifyOutcome])
    and add UNMEASURED/FAILED positive-control tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_ticket_runner_land_release.py
  reason: 'T-2569: update mocks of _verify_ids_passing (frozenset->dict[str,VerifyOutcome])
    and add UNMEASURED/FAILED positive-control tests'
  actor: logan
  at: '2026-08-18'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## What happened

Measured live during T-2534's close, /tmp/t2534_close.log:

    ERROR: run_selected: python runner failed to spawn/timeout
    WARNING: ticket evidence: python verification run failed to execute
      (SpawnFailed: Runner process could not be started or timed out) for [7 nodes]
    WARNING: ticket close: T-2534 evidence no longer passes when re-run: [same 7 nodes]

The runner never started. Zero of the seven nodes were executed. The
close nevertheless reported them as no longer passing.

## Why this is critical

This is the NOT_MEASURED-rendered-as-FAILED confusion that epic T-2391
exists to eliminate, and this instance is worse than a silent zero
because it is a silent FALSE POSITIVE. A silent zero tells you nothing
is wrong when something is; this tells you something IS wrong when
nothing is. An agent reading it concludes its own working code broke and
fixes code that was never broken, potentially weakening a correct test
to make an imaginary failure go away.

It also misdirects diagnosis: the real cause was machine contention
(measured load 48.5 on 12 cores, five agents running gates), which is a
wait-for-a-window problem. The message points at the tests instead.

## Required shape of the fix

SpawnFailed and timeout must NOT collapse into the passes/fails axis.
The evidence re-run result needs the three-way distinction:

    MEASURED(passed) / MEASURED(failed) / NOT_MEASURED(reason)

and ticket close must refuse-and-say-why on NOT_MEASURED rather than
reporting failure. Refusing is correct here: closing on an unmeasurable
batch would be the opposite error.

Positive controls required in both directions:
- a genuinely failing evidence node still reports as failing
- a spawn failure reports as unmeasured and never as failing

## Notes

- Do not fix this by retrying until it spawns. A retry may paper over
  the reporting bug while leaving the same collapse in place for the
  next unmeasurable cause.
- Related: T-2391 (epic), T-2521 (auto-drop caused by a crash being
  byte-identical to a clean run), T-2207 (identity-less quarantine
  record).
