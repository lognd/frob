## Done report

Implemented the sizing-down mechanism T-1436 asks for: `frob_check_delta`
(and its `verify=True` cold cross-check, `_run_verify_pass`) -- the only
`run_gates` call paths that live entirely inside the daemon process --
now cap the process pool at `_DAEMON_GATE_MAX_WORKERS=2` instead of the
normal `min(len(jobs), cpu_count())` bound, via a new private
`_run_gates_bounded(cfg, *, use_cache=False, max_process_workers=None)`
threaded down to `_open_process_pool`'s own new `max_workers` kwarg.
`run_gates` itself keeps its old public signature/behavior byte-for-byte
(it is now a one-line wrapper calling `_run_gates_bounded` with
`max_process_workers=None`) -- every other call site is unaffected.

Verified: `tests/test_serve.py` (38 tests) and the ProcessPoolGates/
RunGates subset of `tests/test_gates.py` (13 tests) pass unchanged.
Confirmed via direct `frob.gates.run_gates`/`_run_gates_bounded` calls
that the DRIFT gate reports 0 stale against the current source+lock
state.

NOT done / disclosed honestly:
- Could not re-measure "warm-daemon vs FROB_NO_DAEMON=1" `frob check
  --only gates --delta --json` parity the ticket's own acceptance
  direction asks for -- that requires running an actual warm daemon
  process and comparing wall-clock/loadavg, which is a live-process
  measurement outside a dispatched sub-agent's sanctioned foreground-
  timeout budget (playbook 3b/3c/6b); it needs a coordinator-run
  before/after comparison, not a unit test.
- Could not add new regression tests in tests/test_gates.py or
  tests/test_serve.py for the new `max_process_workers`/
  `_DAEMON_GATE_MAX_WORKERS` knob: both files are under T-1420's
  standing `tests/**` lease and `frob ticket scope T-1436 --add` refused
  with ScopeLeaseConflict. Same blocker on docs/modules/gates.md and
  docs/modules/serve.md (T-1420 holds a `docs/**` lease), which is why
  `gate:AFFECT` (AFFECT001, run_gates/frob_check_delta's affects()-closure
  docs not touched) and `gate:SCOPE` (SCOPE002, several pre-existing
  symbols in the two widened-scope files whose OWN frob:doc/frob:tests
  targets sit in docs/**/tests/**) do not currently pass a scoped
  `frob check --ticket T-1436` run. This is a real, structural blocker,
  not an oversight -- the fix cannot be gate-clean until T-1420's lease on
  docs/** and tests/** releases (or this ticket's own scope stays
  intentionally narrower and a follow-up ticket adds the docs/tests once
  the lease clears).
- gate:PRE was refreshed via `frob ticket sweep T-1436` after the scope
  widening.
- Filed T-1454 (out of scope, found while investigating a false
  DRIFT001 during this ticket): T-1346's dependency-tracked gate cache
  (use_cache=True, now default-on for every `frob check` call) serves a
  STALE gate:DRIFT/DRIFT001 result across a `frob ack` boundary --
  reproduced directly, `FROB_NO_GATE_CACHE=1` is the workaround used to
  verify this ticket's own change.

Leaving T-1436 OPEN (not closing) given the AFFECT001/SCOPE002 blockers
above are real and not waivable without either touching a leased path or
mischaracterizing the finding.

### Changed
```
 frob.lock                  |  2 +-
 src/frob/gates/__init__.py | 59 ++++++++++++++++++++++++++----
 src/frob/serve/_tools.py   | 32 ++++++++++++++---
 tickets.md                 | 90 ++++++++++++++++++++++++++++++++++++++++++----
 4 files changed, 164 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/test_serve.py::TestRunTouchedTests::test_no_diff_selects_nothing` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProcessPoolGates::test_combined_parallel_path_matches_fully_serial_path` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 3 error(s), 471 warning(s), 729 waived
- error-findings: AFFECT001@src/frob/gates/__init__.py, AFFECT001@src/frob/serve/_tools.py, DRIFT001@src/frob/gates/__init__.py
