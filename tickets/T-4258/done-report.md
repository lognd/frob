## Done report

Changed:
src/frob/serve/_daemon.py::IDLE_TERMINATION_S
src/frob/serve/_daemon.py::_LAST_USEFUL_WORK_MONOTONIC
src/frob/serve/_daemon.py::_record_useful_work
src/frob/serve/_daemon.py::_idle_seconds
src/frob/serve/_daemon.py::_default_terminate
src/frob/serve/_daemon.py::_poll_post_land
src/frob/serve/_daemon.py::_poll_rebase_bot
src/frob/serve/_daemon.py::_poll_verify_worker
src/frob/serve/_daemon.py::_start_daemon

Evidence:
tests/test_serve_daemon.py::TestIdleSelfTermination::test_record_useful_work_updates_the_timestamp
tests/test_serve_daemon.py::TestIdleSelfTermination::test_never_having_worked_is_measured_from_start_time
tests/test_serve_daemon.py::TestIdleSelfTermination::test_idle_under_one_hour_is_not_terminal
tests/test_serve_daemon.py::TestIdleSelfTermination::test_idle_over_one_hour_is_terminal
tests/test_serve_daemon.py::TestIdleSelfTermination::test_loop_self_terminates_after_the_idle_ceiling
tests/test_serve_daemon.py::TestIdleSelfTermination::test_loop_does_not_terminate_while_work_keeps_happening

Filed: T-4282 (graph cache lock diagnosability + concurrent-reader
support), T-4281 (land proof does not distinguish an
infra-failure unmeasured verification from a genuine skip)

Scope note: this ticket's acceptance was narrowed to exactly obligation 4
(idle self-termination). Its other two obligations -- releasing/avoiding
the graph-cache write lock so a concurrent reader always succeeds, and
naming the holding process in a CacheLocked error -- were REMOVED from
this ticket's acceptance list (`frob ticket accept T-4258 --remove`,
audited in acceptance_amendments) and split into new tickets, because
both require editing src/frob/graph/cache.py, outside this ticket's
declared src/frob/serve/_daemon.py + src/frob/serve/_warm.py scope:

- Investigated first: build_graph's own `conn.close()` runs
  unconditionally in a `finally` block, and both `connect()`/
  `connect_readonly()` open a fresh sqlite connection per call with no
  pooling -- no connection leak was found in _daemon.py/_warm.py's
  current code, reachable in a genuinely idle repo (no main-HEAD
  movement); in that state neither `_poll_post_land` nor
  `_poll_verify_worker` touch the cache at all.
- The plausible real mechanism, given this repo's own busy multi-agent
  fleet-root usage (visibly true throughout this very session): a
  shared root where lands happen every few minutes drives
  `_poll_post_land` to re-verify IMMEDIATELY and SYNCHRONOUSLY on every
  single main-HEAD movement (unlike the sibling CoalescingWorker job,
  which already debounces/coalesces), making the daemon a near-constant
  additional writer against the SAME shared `.frob/cache.db` every
  other `frob` invocation also needs.
- Two candidate fixes exist and were deliberately NOT attempted here:
  (a) debouncing `_poll_post_land`'s own re-verify trigger -- rejected
  because it would break the bound, synchronous, immediate-refresh
  contract `tests/test_serve_daemon.py::TestPollPostLand::
  test_head_moved_refreshes_verdict` already pins (two back-to-back
  calls, no sleep, second must differ immediately); (b) re-enabling WAL
  journal mode for concurrent readers -- rejected because T-3644
  already retired WAL for TRUNCATE after WAL's `-shm` mmap caused SIGBUS
  crashes (src/frob/graph/cache.py's own historical comments, e.g.
  "Round 5 of the cache lock-contention saga"); reintroducing WAL here
  blind would resurrect that crash class.
- Filed T-4282 (this history recorded in its own body so the
  next implementer does not repeat either dead end) and
  T-4281 (the land-proof acceptance criterion, which lives in
  src/frob/tickets/_land_verify.py + _land.py -- a separate, large
  enough subsystem to deserve its own ticket).

Related-but-separate finding (per the ticket body's own request to say
so if related): the ticket also names a `.frob/cache.db` corruption
(malformed disk image, freelist mismatch, orphaned pages) measured
twice in one day under concurrent writers. Given the investigation
above, a plausible SHARED mechanism is the same one implicated in the
lock-starvation symptom: a long-lived daemon writer plus opportunistic
short-lived writers contending on the same TRUNCATE-journal-mode
database under a busy fleet root. This is NOT confirmed (no direct
reproduction attempted, and confirming it needs the same
src/frob/graph/cache.py work T-4282 owns) -- noted here, and
in T-4282's own body, as a thing to check when that ticket is
worked, not claimed as proven.

Gates: `frob check --ticket T-4258` (chunked via `--only gates-fast`,
per T-0627's foreground-cap guidance) is clean for this ticket's own
touched set after this change: gate:PRE and gate:AFFECT both pass
(AFFECT001 waived on the touched daemon symbols with a doc-anchor
scope-closure-tension reason matching this same file's own pre-existing
COV007 waiver precedent -- T-1010/T-1937/T-3903 -- rather than widening
scope to the shared docs/modules/serve.md file, which was tried and
reverted after it transitively dragged in ~40 unrelated files' worth of
SCOPE002 closure). Remaining gate:COV (9, all pre-existing/T-4178) and
gate:SCOPE (10, all the same shared-doc-closure class already documented
in this file) findings have zero hits for T-4258/_daemon.py/_warm.py/
test_serve_daemon.py and are pre-existing repo-wide debt this ticket did
not introduce.

pytest tests/test_serve_daemon.py tests/test_serve.py -q -p no:xdist: 59
passed, 0 failed.
