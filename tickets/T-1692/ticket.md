---
id: T-1692
title: 'Backpressure: bound the unverified window by depth and age, and block the
  land at the ceiling'
state: done
kind: feature
origin: agent
created: '2026-08-06'
priority: critical
blocked_by:
- T-1688
parent: T-1686
tier: ticket
sprint: null
scope:
- src/frob/verify/_backpressure.py
- src/frob/app/ticket_runner/_land_cmd.py
- docs/modules/tickets.md
- src/frob/verify/__init__.py
- tests/unit/verify/test_backpressure.py
- tests/unit/test_land_cmd_backpressure.py
- src/frob/verify/_attribution.py
- rapid-debt.jsonl
- src/frob/app/ticket_runner/_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/verify/__init__.py
  reason: backpressure module needs export wiring in verify/__init__.py and its own
    unit tests
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/verify/test_backpressure.py
  reason: backpressure module needs export wiring in verify/__init__.py and its own
    unit tests
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/test_land_cmd_backpressure.py
  reason: unit test for the _land_core_prepare backpressure wiring
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/verify/_attribution.py
  reason: diff-vs-base noise from interleaved T-1753 work in the same worktree session;
    both files are already correct post-T-1753-land, this widens scope defensively
    rather than leaving a SCOPE001 refusal at land time
  actor: logan
  at: '2026-08-07'
- op: add
  glob: rapid-debt.jsonl
  reason: diff-vs-base noise from interleaved T-1753 work in the same worktree session;
    both files are already correct post-T-1753-land, this widens scope defensively
    rather than leaving a SCOPE001 refusal at land time
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: COV002 flagged _attribute_new_findings as changed with no open frob:ticket
    edge -- same diff-base noise as _attribution.py
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/verify/test_backpressure.py::TestCeilingsForProfile::test_fortress_is_zero_depth_zero_age
- tests/unit/verify/test_backpressure.py::TestCeilingsForProfile::test_rapid_is_unbounded
- tests/unit/verify/test_backpressure.py::TestCeilingsForProfile::test_standard_default
- tests/unit/verify/test_backpressure.py::TestCeilingsForProfile::test_standard_toml_override
- tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_empty_queue_is_never_tripped
- tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_depth_ceiling_trips
- tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_age_ceiling_trips
- tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_unbounded_ceilings_never_trip
- tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_queue_unreadable_is_an_error
- tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances::test_not_tripped_returns_immediately_without_draining
- tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances::test_tripped_drains_and_unblocks
- tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances::test_persistently_red_batch_times_out
- tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances::test_unbounded_ceiling_never_blocks
- tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_dry_run_skips_the_check
- tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_not_tripped_is_a_noop
- tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_tripped_blocks_then_proceeds
- tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_block_timeout_logs_and_proceeds
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
---
Deferral is a credit line, not free money. Without this leaf the epic is
a mechanism for accumulating unbounded unverified debt with a pleasant
user experience, which is worse than the synchronous sweep it replaces.

Two independent ceilings, either one sufficient to trip:

- DEPTH: unverified commits above the watermark exceeds K.
- AGE: the oldest unverified entry is older than T.

Both axes are needed. Depth alone lets one commit sit unverified all
weekend behind a dead worker; age alone lets a burst of forty lands
through inside the window.

At the ceiling the land BLOCKS -- waits for the watermark to advance --
rather than failing. A refusal makes the developer re-run the whole land;
a block simply pays back the deferred cost at the moment it came due, and
is the behaviour a bounded queue should have. Log the block loudly with
the current depth, age, and the watermark being waited on, so the wait is
never mysterious. Blocking silently is the one unacceptable outcome.

The ceilings are per-profile settings, which is what the profile-collapse
leaf consumes: fortress K=0, standard K bounded, rapid unbounded.

Acceptance: with K=2, a third land blocks until the worker advances the
watermark, then proceeds; the block emits depth/age/watermark at WARNING;
an unbounded setting never blocks.

Standing repo constraints (binding, not restatement):

- SYMBOLIC, NEVER LEXICAL. Every decision this ticket makes about "which
  code does this concern" must go through the symbol/reference graph
  (frob.graph), never a path-string comparison, filename glob, or regex
  over source text. A lexical shortcut here is a latent wrong answer that
  only shows up under refactor.
- Fallible operations return a typani `Result[T, E]` with a named
  `ErrorSet`. Exceptions only for unrecoverable programmer bugs. Never a
  bare `except` that turns an unknown state into a clean one.
- "Cannot verify" is NEVER "verified". Every unmeasurable outcome must be
  distinguishable from a measured-clean one, in the data model and in the
  logs -- this is the single invariant the whole epic rests on.
- Persisted records are pydantic models with `frozen=True, extra="forbid"`,
  versioned, and forward-compatible on read.
- LOG EVERYTHING WORTH LOGGING: every state change, queue transition,
  boundary crossing, branch, and error path gets a module-logger line per
  ~/.claude/refs/logging.md. Never `print`.
- Docs land in the same change as the code. No follow-up docs ticket.
- No waivers. If a gate fires, fix the cause or fix the gate; a waiver
  here is a structural defect, not a resolution.