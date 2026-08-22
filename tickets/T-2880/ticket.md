---
id: T-2880
title: 'T-2849''s PDEATHSIG fix is loaded but forkservers still leak: 27 new orphans
  in the 49 minutes after it landed, likely an already-started helper that never sees
  the arming env var'
state: queued
kind: bug
origin: agent
created: '2026-08-22'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/process/_reap.py
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
## T-2849's fix is live but the leak continues

T-2849 landed `5dad1ad96` at 04:45:16, arming `PR_SET_PDEATHSIG` at two
levels (helper against launcher at forkserver-preload time, workers against
helper via the pool initializer). Its controls passed with real fork/exec
processes: SIGKILL of the launcher left zero survivors, where before it left
the helper and all workers reparented to init.

Measured ~49 minutes later, on the primary checkout:

    forkservers alive                     54
    spawned AFTER the fix landed          27
    spawned BEFORE the fix landed         15
    (remainder exited between samples)

So new orphans are still being produced at roughly the pre-fix rate.

## What has already been ruled out

- NOT a stale install. The primary venv is editable
  (`__editable__.frob-0.530.0.pth`), `frob.process._reap.__file__` resolves
  to `/home/logan/projects/frob/src/frob/process/_reap.py`, and both
  `arm_parent_death_signal` and
  `_arm_forkserver_helper_pdeathsig_if_requested` are present on the
  imported module.
- NOT stale worktree venvs. All 52 sampled orphans trace to
  `projects/frob/.venv`, the primary checkout's own venv -- none to
  `.claude/worktrees/*/.venv`.
- NOT a second pool implementation in frob. `git grep` for
  `get_context(`/`ProcessPoolExecutor`/`set_start_method`/`forkserver`
  across `src/frob/**/*.py` returns only `_reap.py` itself and
  `arch/_concurrency*.py`, and the latter are REGEX PATTERNS used by the
  arch gate to DETECT pool construction, not construction sites.

So `frob.gates._open_process_pool` remains the only frob-side creator, the
fix is loaded, and the leak persists anyway.

## Leading hypothesis, to be tested rather than assumed

`multiprocessing`'s forkserver helper is started LAZILY and cached per
context, process-wide. `_open_process_pool` stamps
`FORKSERVER_ARM_PDEATHSIG_ENV` into the environment immediately before
constructing its pool -- but if ANY earlier code in the same process has
already caused the forkserver context to start its helper, that helper was
spawned without the env var and is therefore unarmed. The pool then reuses
the already-running unarmed helper, and the `_FORKSERVER_PRELOAD` import
hook never fires for it.

That would explain the exact observed shape: the mechanism is correct and
its isolated controls pass (a fresh process, fresh helper, env set first),
while the real `frob check` path -- which does substantial work before
opening its pool -- gets an unarmed helper.

Test it directly: instrument whether the helper's arming hook actually runs
during a real `frob check`, rather than in an isolated repro. If the helper
is pre-started, the fix needs to arm it at context-creation time or force a
fresh context.

## Do not

- Do not weaken or revert T-2849. Its mechanism is right and its controls
  are real; the gap is where/when the env var is visible, not the design.
- Do not "fix" this by making the periodic reaper more aggressive. Reaping
  is the mitigation that already exists (T-2443/T-2818) and it demonstrably
  cannot keep pace -- roughly 150 orphans were reaped by hand in one session,
  twice recovering the box from ~1.6GB available RAM with all lands stalled.

## Positive controls, both directions

- A real `frob check` (not an isolated repro) whose launcher is SIGKILLed
  leaves ZERO forkserver survivors. This is the case that still fails.
- A real `frob check` that exits cleanly also leaves zero.
- A forkserver belonging to a genuinely RUNNING check is never killed, at
  any ancestry depth -- reuse T-2818's `_forkserver_root_is_live_check`
  ancestry oracle rather than redefining orphan-ness.

## Measurement discipline

Count only after verifying zero live `frob check` processes, and abort the
measurement if any appear. RSS reads near zero for swapped processes -- sum
`VmSwap` instead (T-2517). Compare ages against the fix's own land time to
distinguish pre-existing orphans from newly-created ones; that comparison is
what showed the fix was not holding.
