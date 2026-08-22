## Done report

Changed:
src/frob/process/_reap.py::arm_parent_death_signal
src/frob/process/_reap.py::_arm_forkserver_helper_pdeathsig_if_requested
src/frob/process/_reap.py::FORKSERVER_ARM_PDEATHSIG_ENV
src/frob/gates/__init__.py::_stamp_forkserver_pdeathsig_env
src/frob/gates/__init__.py::_worker_arm_pdeathsig
src/frob/gates/__init__.py::_open_process_pool (wired the two above; added initializer=)
docs/modules/process.md (Forkserver reaping section: T-2849 mechanism prose)
design/frob.strata (node core env.read via-list: added src/frob/process/_reap.py)

Evidence:
tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_arms_successfully_on_linux
tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_self_kills_on_missed_reparent_race
tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_returns_false_off_linux
tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested::test_noop_without_env_var
tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested::test_arms_when_env_var_set
tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested::test_success_logs_nothing_at_all
tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested::test_failure_still_warns

Root cause (matches the failure log's own diagnosis, re-verified before
implementing): frob.gates._open_process_pool's forkserver start method
leaks its helper + worker processes when the frob check launcher is
SIGKILLed -- reproduced directly, a bare multiprocessing.get_context(
"forkserver") pool killed with kill -9 left the helper and all workers
alive, reparented to init. T-2443's existing mitigation is SIGTERM-only
by construction and cannot reach this path.

The trap this ticket's failure log flagged: a forkserver WORKER's real
OS parent is the persistent forkserver HELPER, not the launcher (workers
are raw fork()ed from the helper, never exec()ed). Arming PR_SET_
PDEATHSIG only on workers would track the helper's death, not the
launcher's.

Fix: arm PR_SET_PDEATHSIG at BOTH hops, chaining launcher death across
the helper. _open_process_pool stamps FORKSERVER_ARM_PDEATHSIG_ENV
before constructing the pool; the freshly-started forkserver helper
(named in _FORKSERVER_PRELOAD, imported once at helper startup) arms
itself against the launcher, its real OS parent
(_arm_forkserver_helper_pdeathsig_if_requested). The pool's initializer
(_worker_arm_pdeathsig) arms every worker against the helper, ITS real
OS parent. Launcher death by any means, including SIGKILL, now
cascades: helper dies, then every worker dies in turn -- no finally/
atexit involved anywhere in the chain. Both call sites route through
one shared primitive, arm_parent_death_signal (ctypes prctl, with a
self-kill fallback for the fork/prctl race window).

Positive controls, both directions, measured with real fork/exec
processes (not simulated):
- A SIGKILLed launcher leaves ZERO forkserver/worker survivors
  (previously left both, reparented to init, confirmed before the fix).
- A cleanly-exiting launcher also leaves zero (unchanged).
- A genuinely running pool's helper/workers are NEVER touched while the
  launcher stays alive (verified while the launcher was still running,
  workers survived; only killing the launcher tore them down).

Did not reuse T-2818's _forkserver_root_is_live_check ancestry oracle:
that governs the PERIODIC REAP decision (reap_orphaned_forkservers),
untouched by this ticket. This fix is structural/preventive (kernel-
level signal propagation), so no new "is this orphaned" decision was
written -- no duplication of that rule.

Self-found and fixed during validation (not in the original ticket):
the helper-arm success path originally logged at DEBUG
(_arm_forkserver_helper_pdeathsig_if_requested), which fires at
forkserver PRELOAD time -- before frob.gates._run_process_gate's T-0806
per-job stdout clamp has ever run for that process. Reproduced this
leaking a raw log line into a real `frob check --json` capture,
contaminating the JSON. Fixed by making the success path silent
(matching arm_parent_death_signal's own no-log-on-success convention);
the failure branch stays a _log.warning, which is safe (goes to stderr
per this repo's own logging config, not stdout). Added
test_success_logs_nothing_at_all / test_failure_still_warns as
regression controls for both directions.

Filed: T-2875 (frob.graph.dsl._RESERVED_MARKER_VERBS omits
"callee-raises", so the required `# frob:callee-raises` marker on the
new libc.prctl(...) call falsely fires DSL001 "unknown verb" -- the
module's own comment claims this can't happen for a same-line trailing
comment; reproduced that this is false for a bare-text comment, both
placements. Workaround applied at the one call site: frob:waive DSL001
citing this ticket. Out of T-2849's own scope (src/frob/graph/dsl.py),
filed rather than fixed).

Scope: amended via `frob ticket scope --add` (not follow-up tickets, per
explicit coordinator direction) for docs/modules/process.md (AFFECT001/
COV001/ENV001 doc anchor for the new public constant + two changed
functions), tests/unit/test_process_reap.py (the ticket's own new unit
tests), and design/frob.strata (SELFAUDIT001/SYS100 -- the new env.read
capability this ticket's own code introduces on node core, main had
zero env reads in src/frob/process/_reap.py before this change).

Gates: `frob check --ticket T-2849` clean on all five scoped files as of
the final pre-land run -- the only remaining findings at land time were
pre-existing red-tree fallout (frob-core Rust-split doc drift already
tracked as T-2855, and unrelated design/frob.strata flow declarations
this diff never touches) plus routine draft-ticket-filing SCOPE001 noise
for the T-2875 ledger file frob ticket land absorbs.

### Changed
```
 design/frob.strata                 |   2 +-
 docs/modules/process.md            |  42 ++++++++++
 src/frob/gates/__init__.py         |  69 ++++++++++++++++-
 src/frob/process/_reap.py          | 152 ++++++++++++++++++++++++++++++++++++-
 tests/unit/test_process_reap.py    | 109 ++++++++++++++++++++++++++
 tickets/T-2849/ticket.md           |   8 ++
 tickets/T-2875/ticket.md |  40 ++++++++++
 7 files changed, 418 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_arms_successfully_on_linux` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_self_kills_on_missed_reparent_race` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_returns_false_off_linux` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested::test_noop_without_env_var` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested::test_arms_when_env_var_set` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested::test_success_logs_nothing_at_all` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested::test_failure_still_warns` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 28 error(s), 1017 warning(s), 805 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@design/frob.strata, COV003@tickets/T-1102, COV003@tickets/T-1651, COV003@tickets/T-1656, COV003@tickets/T-2375, COV003@tickets/T-2822, COV003@tickets/T-2823, COV003@tickets/T-2824, COV003@tickets/T-2825, COV003@tickets/T-2826, COV003@tickets/T-2829, COV003@tickets/T-2830, COV003@tickets/T-2839, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/claude-hooks.md, DOC006@docs/modules/graph.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DOCENUM001@docs/modules/gates.md, DRIFT002@docs/modules/tickets-landing.md, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PRE001@tickets/T-2849, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
