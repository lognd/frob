---
id: T-2849
title: 'frob check leaks its multiprocessing forkservers: ~150 orphans reaped by hand
  in one session, once reaching 16.7GB swap and stalling all lands for 45 minutes'
state: done
kind: bug
origin: agent
created: '2026-08-21'
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
- src/frob/__main__.py
- docs/modules/process.md
- tests/unit/test_process_reap.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/check/
  reason: 'Original scope src/frob/check/ was wrong -- I set it without checking.
    Measured: that package contains NO multiprocessing/ProcessPoolExecutor/forkserver
    code, only concurrent.futures.ThreadPoolExecutor which shares the parent OS process
    and cannot orphan. The leaking pool is frob.gates._open_process_pool / _process_pool_start_method
    in src/frob/gates/__init__.py; the existing SIGTERM-only mitigation is install_sigterm_reaper
    / reap_orphaned_forkservers in src/frob/process/_reap.py, wired from src/frob/__main__.py.
    Retargeting to those three files so the ticket is implementable.'
  actor: logan
  at: '2026-08-22'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'Original scope src/frob/check/ was wrong -- I set it without checking.
    Measured: that package contains NO multiprocessing/ProcessPoolExecutor/forkserver
    code, only concurrent.futures.ThreadPoolExecutor which shares the parent OS process
    and cannot orphan. The leaking pool is frob.gates._open_process_pool / _process_pool_start_method
    in src/frob/gates/__init__.py; the existing SIGTERM-only mitigation is install_sigterm_reaper
    / reap_orphaned_forkservers in src/frob/process/_reap.py, wired from src/frob/__main__.py.
    Retargeting to those three files so the ticket is implementable.'
  actor: logan
  at: '2026-08-22'
- op: add
  glob: src/frob/process/_reap.py
  reason: 'Original scope src/frob/check/ was wrong -- I set it without checking.
    Measured: that package contains NO multiprocessing/ProcessPoolExecutor/forkserver
    code, only concurrent.futures.ThreadPoolExecutor which shares the parent OS process
    and cannot orphan. The leaking pool is frob.gates._open_process_pool / _process_pool_start_method
    in src/frob/gates/__init__.py; the existing SIGTERM-only mitigation is install_sigterm_reaper
    / reap_orphaned_forkservers in src/frob/process/_reap.py, wired from src/frob/__main__.py.
    Retargeting to those three files so the ticket is implementable.'
  actor: logan
  at: '2026-08-22'
- op: add
  glob: src/frob/__main__.py
  reason: 'Original scope src/frob/check/ was wrong -- I set it without checking.
    Measured: that package contains NO multiprocessing/ProcessPoolExecutor/forkserver
    code, only concurrent.futures.ThreadPoolExecutor which shares the parent OS process
    and cannot orphan. The leaking pool is frob.gates._open_process_pool / _process_pool_start_method
    in src/frob/gates/__init__.py; the existing SIGTERM-only mitigation is install_sigterm_reaper
    / reap_orphaned_forkservers in src/frob/process/_reap.py, wired from src/frob/__main__.py.
    Retargeting to those three files so the ticket is implementable.'
  actor: logan
  at: '2026-08-22'
- op: add
  glob: docs/modules/process.md
  reason: new public constant FORKSERVER_ARM_PDEATHSIG_ENV and the two changed functions
    arm_parent_death_signal/_arm_forkserver_helper_pdeathsig_if_requested owe a doc
    anchor under the existing forkserver-reaping-t-2443 section; incomplete work per
    AFFECT001/COV001/ENV001, not out-of-scope work
  actor: logan
  at: '2026-08-22'
- op: add
  glob: tests/unit/test_process_reap.py
  reason: unit tests for arm_parent_death_signal / _arm_forkserver_helper_pdeathsig_if_requested
    / the leak-regression stdout-contamination controls belong in this ticket's own
    scope, not filed separately
  actor: logan
  at: '2026-08-22'
- op: add
  glob: tests/unit/test_process_reap.py
  reason: unit tests for arm_parent_death_signal / _arm_forkserver_helper_pdeathsig_if_requested
    / the leak-regression stdout-contamination controls belong in this ticket's own
    scope, not filed separately
  actor: logan
  at: '2026-08-22'
- op: add
  glob: tests/unit/test_process_reap.py
  reason: unit tests for arm_parent_death_signal / _arm_forkserver_helper_pdeathsig_if_requested
    / the leak-regression stdout-contamination controls belong in this ticket's own
    scope, not filed separately
  actor: logan
  at: '2026-08-22'
- op: add
  glob: tests/unit/test_process_reap.py
  reason: unit tests for arm_parent_death_signal / _arm_forkserver_helper_pdeathsig_if_requested
    / the leak-regression stdout-contamination controls belong in this ticket's own
    scope, not filed separately
  actor: logan
  at: '2026-08-22'
- op: add
  glob: design/frob.strata
  reason: the new os.environ.get read in _arm_forkserver_helper_pdeathsig_if_requested
    is a genuinely new env.read capability use on src/frob/process/_reap.py (main
    has zero env reads in this file today); SELFAUDIT001/SYS100 requires it declared
    on node core's env.read via-list, incomplete work per this ticket's own new code,
    not out-of-scope
  actor: logan
  at: '2026-08-22'
evidence:
- tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_arms_successfully_on_linux
- tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_self_kills_on_missed_reparent_race
- tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_returns_false_off_linux
- tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested::test_noop_without_env_var
- tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested::test_arms_when_env_var_set
- tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested::test_success_logs_nothing_at_all
- tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested::test_failure_still_warns
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 5dad1ad96008f66d9b169a001a1464aaabed8083
---
## The gap

T-2443 and T-2818 made this leak VISIBLE and reapable. Neither stops it
happening. `fleet_status` now prints, correctly:

    ORPHANED FORKSERVERS: 44 do not have a live `frob check` anywhere in
    their ancestry (T-2443/T-2818 leak signature -- SIGTERM them or wait
    for the next `frob check`'s own startup reaper)

So the diagnosis is solved and the remediation is manual (or deferred to a
startup reaper that is demonstrably not keeping pace). The processes should
not be orphaned in the first place.

## Measured across one session, 2026-08-21

Coordinator observations, each after verifying ZERO live `frob check`
processes before counting:

    10:47   92 orphaned, 16.7GB swap, 1.6GB RAM available -> reaped 90
                                       -> 3.2GB swap, 18.7GB available
    20:52   12 orphaned                -> reaped 12
    21:44   53 orphaned
    23:33   44 orphaned,  7.2GB swap,  8.7GB available

Roughly 150 orphans reaped by hand over the session, recovering 10-13GB each
time. Accumulation is on the order of tens per hour under a 5-agent fleet.

The 10:47 instance was not merely wasteful: the box reached 1.6GB available
with ZERO lands completing for 45 minutes. It presented as agent stalls, and
I spent that time investigating the wrong cause because the detector of the
day reported `0 orphaned` (the one-level-parent bug T-2818 later fixed).

## What to determine

1. WHY are they orphaned? A `frob check` that exits cleanly should tear down
   its own `multiprocessing` pool. Establish whether the leak is on the
   clean-exit path, the SIGKILL/timeout path (lands are killed at the 540s
   wrapper routinely), or both. Instrument rather than infer -- the answer
   changes the fix entirely.
2. The killed-land path is the prime suspect and is worth checking first:
   agents' lands are SIGKILLed by their shell wrapper with some regularity,
   and a SIGKILLed parent cannot run cleanup. If that is the dominant
   source, the fix belongs in how the pool is created (e.g. a parent-death
   signal so children die with their parent) rather than in teardown code
   that never gets to run.
3. Why is the existing startup reaper not keeping pace? It is cited in
   fleet_status's own message, so it exists. Measure what it actually
   reaps and when.

## Required shape

Prefer a mechanism that cannot be skipped over one that runs at exit.
Teardown code does not execute when the process is killed, which is
precisely the case that matters here. On Linux, `prctl(PR_SET_PDEATHSIG)`
or an equivalent parent-death mechanism makes orphaning structurally
impossible rather than merely tidied-up-later.

Whatever is chosen must not reap a forkserver belonging to a LIVE check.
T-2818 already implements the correct ancestry test
(`_forkserver_root_is_live_check`, bounded chain walk) -- reuse it rather
than writing a second definition. Two homes for that rule will desync, and
the consequence of getting it wrong is killing live workers mid-check, which
is far worse than the leak.

## Positive controls, both directions

- A `frob check` that is SIGKILLed mid-run leaves ZERO orphaned forkservers.
  Plant it: start a check, kill -9 the parent, count survivors. This is the
  case that fails today.
- A `frob check` that exits cleanly also leaves zero.
- A forkserver belonging to a genuinely RUNNING check is never killed, at
  any ancestry depth. Without this control the fix reaps live work.

## Note on measurement discipline

Count only after verifying zero live checks, and treat any nonzero live-check
count as a reason to abort the measurement. RSS reads near zero for swapped
processes, so sum `VmSwap` rather than RSS when quantifying the cost
(T-2517 established this).

## Failure log
- 2026-08-22 attempt 1: SCOPE IS WRONG and the suggested mechanism is FALSIFIED -- measured 2026-08-22, no code change possible as scoped. (1) src/frob/check/ contains NO multiprocessing/ProcessPoolExecutor/forkserver code at all, only concurrent.futures.ThreadPoolExecutor at src/frob/check/__init__.py:608,1024 which shares the parent OS process and structurally cannot orphan. The leaking pool is frob.gates._open_process_pool / _process_pool_start_method in src/frob/gates/__init__.py; the existing insufficient mitigation is install_sigterm_reaper / reap_orphaned_forkservers in src/frob/process/_reap.py, wired from src/frob/__main__.py. Correct scope is those three files, NOT src/frob/check/. (2) T-2443's reaper is SIGTERM-only: a signal.signal handler can never run on SIGKILL by construction, and reap_orphaned_forkservers is a once-per-invocation, 300s-age-floored best-effort sweep -- which is why it cannot keep pace with tens of leaks per hour. (3) SIGKILL control PLANTED AND CONFIRMED: a bare multiprocessing.get_context('forkserver') parent with 3 workers, killed with kill -9, left the forkserver helper and all 3 workers alive, verified by ps/pgrep before and after. (4) CRITICAL TRAP that falsifies the PR_SET_PDEATHSIG mechanism suggested in this ticket body: a forkserver-spawned worker's OS parent is the PERSISTENT FORKSERVER HELPER, not the frob check launcher -- workers are fork()ed inside the helper and never exec()ed, so they even inherit the helper's /proc/pid/cmdline. PR_SET_PDEATHSIG fires only on death of the DIRECT OS parent, so adding it to the pool's worker initializer would track the helper's death rather than the launcher's and would NOT fix the leak. Any implementer must solve launcher-death propagation across that intermediate helper. Reuse T-2818's _forkserver_root_is_live_check ancestry oracle rather than redefining orphan-ness.