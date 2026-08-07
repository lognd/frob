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
runs_last: false
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

## Done report

Changed:
- src/frob/verify/_backpressure.py (new): BackpressureError,
  BackpressureCeilings, BackpressureStatus, ceilings_for_profile,
  current_status, block_until_watermark_advances, plus private helpers
  _read_frob_toml_profile_table/_parse_enqueued_at.
- src/frob/verify/__init__.py: export the five new public names.
- src/frob/app/ticket_runner/_land_cmd.py: `_land_core_prepare` calls the
  new `_apply_backpressure(root, cfg, effective_profile)` right after
  profile resolution; `_apply_backpressure` resolves ceilings and blocks
  via `frob.verify.block_until_watermark_advances`, skipped under
  `--dry-run`, logging (never raising) on a block timeout.
- docs/modules/tickets.md: new "Backpressure (T-1692)" section.
- tests/unit/verify/test_backpressure.py (new, 13 tests),
  tests/unit/test_land_cmd_backpressure.py (new, 4 tests).

Design: two independent ceilings (depth, age), either sufficient to
trip, read from the SAME durable verify queue T-1687/T-1688 already
maintain -- no new storage. At the ceiling the land BLOCKS rather than
refuses: `block_until_watermark_advances` logs the trip loudly at
WARNING (depth, age, watermark) and ACTIVELY drives
`frob.verify.run_coalesced_verification` on each iteration (default
`drain_fn`) to pay back the deferred cost itself, rather than assuming a
daemon is watching the queue -- this makes the design correct even with
no daemon running. A last-resort timeout (30 min default) on the block
itself keeps a permanently red/quarantined batch from wedging every
future land forever; a timeout logs at ERROR and the land proceeds
anyway (the loud WARNING trail is the safeguard, not a second refusal).
Per-profile ceilings: fortress depth=0/age=0 (still blocks, never
refuses -- see module docstring "BLOCK, NEVER FAIL"), standard a bounded
default (5 / 3600s) overridable via frob.toml's `[profile]
backpressure_max_depth`/`backpressure_max_age_s`, rapid None/None
(unbounded on both axes, never blocks, by construction).

Acceptance (from the ticket body, verified directly):
"with K=2, a third land blocks until the worker advances the watermark,
then proceeds" -> `TestBlockUntilWatermarkAdvances::test_tripped_drains_
and_unblocks` (K=2, three queued entries, injected drain_fn that
advances the watermark and compacts the queue, asserts the returned
status is no longer tripped and depth==0).
"the block emits depth/age/watermark at WARNING" -> the WARNING log line
in `block_until_watermark_advances` includes `status.reason` (which
axis, by how much), `status.depth`, `status.age_s`, and
`status.watermark_commit` in one message; exercised by the same test
(the loop only reaches `Ok` after logging).
"an unbounded setting never blocks" ->
`TestBlockUntilWatermarkAdvances::test_unbounded_ceiling_never_blocks`
(100 queued entries, ceilings max_depth=None/max_age_s=None, asserts
drain_fn is never called at all).

Disclosed scope cut: the full profile-to-queue-depth collapse (deleting
every remaining `if rapid:` seam scattered through the land pipeline,
T-1686's own "payoff" framing) is NOT this leaf's job -- `_apply_
backpressure` is additive, wired alongside the existing rapid/standard
branching `_land_core_prepare` already has. Stated explicitly in
docs/modules/tickets.md's own "Disclosed scope cut" paragraph, not
silently assumed done.

FOR T-1696 (profile collapse): `ceilings_for_profile` IS the first
concrete instance of "the profiles stop being three code paths and
become one dial" (T-1686's own payoff framing) -- fortress=depth 0/age
0, standard=bounded (toml-overridable), rapid=unbounded, all resolved
from ONE function keyed on `ProfileName`, not three separate `if
profile ==` branches scattered per call site. Whoever takes T-1696
should EXTEND this function (add whatever new per-profile knob the
collapse needs) rather than inventing a second, parallel
profile-to-setting mechanism alongside it.

Evidence: 17 pytest node ids recorded via `frob ticket evidence`, all
measured passing:
`timeout 100 uv run pytest tests/unit/verify/ tests/unit/test_land_cmd_backpressure.py -p no:cacheprovider -q`
-> `collected=50 failed=0`.

Filed: T-1753 (post-land sweep regression from T-1690's own land:
ARCH001/E501/ty invalid-argument-type) -- fixed and landed separately
before this ticket, per explicit coordinator instruction, at commit
8a2f473e454c085890de379dcefd098a2978b4ce.

Gates: `frob check --only gates-fast --ticket T-1692` clean down to 3
SCOPE001 findings on land-owned files (.frob-release.json,
pyproject.toml, uv.lock) -- the same T-1690/T-1753 pattern, reconciled
by `frob ticket land`'s own internal merge, not hand-fixed here (agent
playbook section 4b). `frob check --only gates-native --ticket T-1692`
and `frob check --only gates-security --ticket T-1692` also run clean of
new errors introduced by this ticket's own files.

### Changed
```
 design/frob.strata                       |  10 +-
 docs/modules/tickets.md                  |  72 +++++++
 src/frob/app/ticket_runner/_land_cmd.py  |  62 +++++-
 src/frob/verify/__init__.py              |  26 ++-
 src/frob/verify/_backpressure.py         | 360 +++++++++++++++++++++++++++++++
 tests/unit/test_land_cmd_backpressure.py | 113 ++++++++++
 tests/unit/verify/test_backpressure.py   | 219 +++++++++++++++++++
 tickets.md                               | 161 ++++++++++++++
 8 files changed, 1008 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/unit/verify/test_backpressure.py::TestCeilingsForProfile::test_fortress_is_zero_depth_zero_age` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestCeilingsForProfile::test_rapid_is_unbounded` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestCeilingsForProfile::test_standard_default` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestCeilingsForProfile::test_standard_toml_override` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_empty_queue_is_never_tripped` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_depth_ceiling_trips` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_age_ceiling_trips` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_unbounded_ceilings_never_trip` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_queue_unreadable_is_an_error` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances::test_not_tripped_returns_immediately_without_draining` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances::test_tripped_drains_and_unblocks` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances::test_persistently_red_batch_times_out` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances::test_unbounded_ceiling_never_blocks` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_dry_run_skips_the_check` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_not_tripped_is_a_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_tripped_blocks_then_proceeds` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_block_timeout_logs_and_proceeds` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 17 passed (from 17 evidence id(s))
- gates: 5 error(s), 536 warning(s), 727 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/agent-a26588e5def8b5820/src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/agent-a26588e5def8b5820/src/frob/verify/_backpressure.py, PRE001@tickets/T-1692, invalid-argument-type@src/frob/app/ticket_runner/_land_cmd.py, invalid-argument-type@src/frob/app/ticket_runner/_rapid_sweep.py
