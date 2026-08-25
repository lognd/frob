---
id: T-2880
title: 'T-2849''s PDEATHSIG fix is loaded but forkservers still leak: 27 new orphans
  in the 49 minutes after it landed, likely an already-started helper that never sees
  the arming env var'
state: done
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
- src/frob/process/_reap.py
- tests/unit/test_process_reap.py
- docs/modules/process.md
evidence_scope:
- tests/unit/test_process_reap.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/__init__.py
  reason: narrowing to only the file actually touched by the fix (process/_reap.py),
    plus the test file and doc anchor the fix updates; gates/__init__.py was never
    edited (attempts 1/2 already found the mechanism correct there, root cause is
    in the arm-race check itself)
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/unit/test_process_reap.py
  reason: narrowing to only the file actually touched by the fix (process/_reap.py),
    plus the test file and doc anchor the fix updates; gates/__init__.py was never
    edited (attempts 1/2 already found the mechanism correct there, root cause is
    in the arm-race check itself)
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/modules/process.md
  reason: narrowing to only the file actually touched by the fix (process/_reap.py),
    plus the test file and doc anchor the fix updates; gates/__init__.py was never
    edited (attempts 1/2 already found the mechanism correct there, root cause is
    in the arm-race check itself)
  actor: logan
  at: '2026-08-25'
evidence:
- tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_self_kills_when_already_reparented_before_entry
designated_repro_test: tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_self_kills_when_already_reparented_before_entry
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: ac34642515312b8f3024153ecda17e962a5f1c32
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

## Failure log
- 2026-08-22 attempt 1: Leading hypothesis (already-started helper never sees the arming env var, same process) tested directly and FALSIFIED for the two in-scope files own call path. Real unbudgeted frob check --only gates run, instrumented _stamp_forkserver_pdeathsig_env and _arm_forkserver_helper_pdeathsig_if_requested (reverted after, worktree clean): the stamp fires once, immediately before pool construction; the one forkserver helper spawned inherits the env marker and arms correctly, every time, across two separate real runs. Both call sites are the sole creator in this codebase (grepped). Synthetic real fork/exec race harness reproducing the exact pool/initializer shape, SIGKILL at 0/1/5/10/20/50/100ms after worker spawn (probing the fork-clears-PR_SET_PDEATHSIG window): zero survivors at every delay across all trials. Could not manufacture the leak even targeting the one theoretically real race window. Ruled out (already in ticket body, re-confirmed by code reading): daemon persistence -- frob_check_delta runs only inside the long-lived warm daemon, and its version-skew self-heal is driven by importlib.metadata.version, unaffected by a source-only fix with no version bump (confirmed T-2849 landing commit never touched pyproject.toml) -- a real, independently-confirmed defect, filed separately as T-2884 (scope frob.app._daemon_proxy / frob.serve._socketd) since its fix lives outside T-2880's two-file scope. Cannot be this ticket's dominant mechanism though: FROB_DAEMON is opt-in and not set anywhere in this fleet's config, and no live daemon was found running. Within T-2880's declared scope the PDEATHSIG mechanism is correct and I could not make it fail on a real check or in a targeted race harness. Failing rather than forcing an in-scope change with no evidence behind it. Recommend the coordinator either widen scope to include frob.serve/frob.app and pursue T-2884 as the real fix, or capture a live pid/cmdline/parent chain from the actual fleet run at the moment of a real leak, since neither a clean real check nor a tight synthetic race reproduces it here.
- 2026-08-22 attempt 2: ROOT CAUSE FOUND -- the fix is CORRECT but not DEPLOYED to stale worktrees. The prior attempt correctly falsified the pre-started-helper hypothesis by instrumenting a real frob check, and its measurement stands: the env stamp fires before pool construction and the helper arms every time. What it could not see from inside its own worktree is that each worktree carries its OWN editable install pointing at THAT worktree's src/, not main's. Measured on the primary checkout 2026-08-22: 9 worktrees have arm_parent_death_signal in their own src/frob/process/_reap.py, 21 DO NOT (dev-friction, t-1614, t-1778, t-1945, t-2489, t-2490, t-2508, t-2523, t-2547, t-2612, t-2778, and 10 more). Any agent running frob check from one of those 21 runs PRE-FIX pool-construction code and leaks exactly as before, which is why orphans kept appearing after the land. Corroborating live ancestry capture: of ~40 sampled forkservers, 15 were reparented to init (genuine orphans) and 15 traced to a single investigating worktree's venv. This also explains why the synthetic race harness found zero survivors at every SIGKILL delay -- the harness ran post-fix code. IMPLICATION: this is a deployment/staleness problem, not a mechanism problem. Do NOT re-test the CLI path and do NOT weaken T-2849. The remaining questions are (a) whether stale worktrees should be refused, refreshed, or reaped, noting many of the 21 are already flagged IDLE/STALE by fleet_status and some are weeks old, and (b) whether this generalises -- a stale worktree runs stale code for EVERY fix, not just this one, so any land whose correctness depends on all agents running it is affected. That second question is the larger finding and may deserve its own ticket.