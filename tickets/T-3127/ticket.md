---
id: T-3127
title: Make the T-1514 pre-commit unscoped sweep stage-capable so the disposable-stage
  flip covers non-rapid profiles
state: queued
kind: feature
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3121 flipped the squash-apply transaction onto a disposable worktree,
but DELIBERATELY carved out the path where a `pre_commit_sweep` is
supplied (every land profile except `rapid`): that sweep,
`_pre_commit_unscoped_error_sweep`, spawns an unscoped `frob check --json`
in whatever directory it is handed. A freshly-cut disposable worktree has
no `.venv`, no built natives and no `.frob` cache, so the spawn would
either report `unmeasurable` -- silently disabling a guard, the exact
silent-zero shape this repo has been burned by repeatedly -- or report
mass phantom findings and falsely refuse every land. Handing it `root`
instead would be worse still: under the flip `root` does not hold the
staged changeset at all, so the sweep would return a clean answer about
the wrong tree.

So today a non-rapid profile silently keeps the OLD in-root behavior and
gets none of T-3121's contention win. This is a real gap, disclosed
rather than hidden: see the "What deliberately did NOT move" section of
docs/modules/tickets-landing.md#the-disposable-stage-flip-t-3121 and the
carve-out branch in `_squash_apply_on_disposable_stage`.

The fix is to make the sweep stage-capable. Options worth measuring
before choosing: provision the disposable stage enough for a `frob check`
spawn (symlink the root's `.venv` and `.frob` in, which is cheap but
couples the stage to root's state); or run the check in-process against
the stage rather than spawning; or diff-drive the sweep from the composed
commit instead of from a checkout at all.

Acceptance: with a non-rapid profile configured, a land engages the
disposable stage AND the T-1514 sweep measures the stage's real staged
changeset -- proven by a must-fire fixture where a genuine new unscoped
error in the staged tree still refuses the land, and a must-stay-quiet
fixture where a clean staged tree does not.

## Failure log
- 2026-08-27 attempt 1: MEASURED, not reasoned: across four provisioning levels a disposable stage NEVER returned a MEASURED sweep answer, each level swapping one unmeasurable cause for the next -- (1) bare stage: spawn timed out, 371.2s, None; (2) + root .venv symlink + copied cache.db: 4 stage groups deferred (gates-native, gates-security, lint, static), 0.9s, None; (3) + cache meta.root retargeted to the stage: 1 group (static) deferred, 91.7s, None; (4) second run on its own warm cache at budget 480: pre-gate abort, no gate-summary at all (native-staleness class -- the symlinked venv's natives were built from a different tree), 79.5s, None. CONTROL, the same probe against the real root: MEASURED, 78 error identities, 257.4s then 130.3s on a second sample, identical identity set both times. So the sweep is genuinely measurable in root and genuinely NOT measurable in any cheaply-provisioned stage; provisioning is a real lever (0.9s of planning became 91.7s of actual gate work) but the last two blockers are structural, not budgetary: the chunker's timing model has no headroom in a fresh tree, and native staleness aborts before gates whenever the interpreter's natives came from a different checkout. Every one of those four failures is the silent shape this repo has been burned by -- a guard reporting success because it could not run. T-3121's carve-out therefore stands, now backed by measurement instead of argument. Filed the design that could actually work (a persistent, reused warm sweep stage rather than a fresh disposable one per land) rather than forcing a flip whose failure mode is an invisibly disabled guard. Follow-up filed as T-3135 (persistent warm sweep stage).
