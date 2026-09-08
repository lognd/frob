---
id: T-4258
title: the serve daemon holds an exclusive write lock on the graph cache for its whole
  lifetime, starving every other process's graph build into a silent unmeasured pass
state: in-progress
kind: bug
origin: human
created: '2026-09-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/serve/_daemon.py
- src/frob/serve/_warm.py
- tests/test_serve_daemon.py
- tests/test_serve.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_serve_daemon.py
  reason: test file for _daemon.py's new idle-self-termination code, required by frob:tests
    directives added in the same change
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/serve.md
  reason: 'scope closure: pre-existing frob:doc/frob:tests targets for symbols touched
    in this file (docstring/doc anchors and _warm.py''s own bound tests), flagged
    by SCOPE002 after adding tests/test_serve_daemon.py'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: 'scope closure: pre-existing frob:doc/frob:tests targets for symbols touched
    in this file (docstring/doc anchors and _warm.py''s own bound tests), flagged
    by SCOPE002 after adding tests/test_serve_daemon.py'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_serve.py
  reason: 'scope closure: pre-existing frob:doc/frob:tests targets for symbols touched
    in this file (docstring/doc anchors and _warm.py''s own bound tests), flagged
    by SCOPE002 after adding tests/test_serve_daemon.py'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: docs/modules/serve.md
  reason: 'reverting: docs/modules/serve.md and docs/modules/tickets-verify-sweep.md
    are monolithic shared docs whose own SCOPE002 closure drags in nearly the entire
    serve/verify/tickets subsystem transitively (37 more files) -- the same ''out
    of proportion'' tension this file''s own pre-existing COV007 waivers already document
    for T-1010/T-1937/T-3903/T-1895/T-3847. Waiving AFFECT001 on the touched symbols
    instead, matching that precedent, rather than expanding scope to the whole shared-doc
    closure'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: docs/modules/tickets-verify-sweep.md
  reason: 'reverting: docs/modules/serve.md and docs/modules/tickets-verify-sweep.md
    are monolithic shared docs whose own SCOPE002 closure drags in nearly the entire
    serve/verify/tickets subsystem transitively (37 more files) -- the same ''out
    of proportion'' tension this file''s own pre-existing COV007 waivers already document
    for T-1010/T-1937/T-3903/T-1895/T-3847. Waiving AFFECT001 on the touched symbols
    instead, matching that precedent, rather than expanding scope to the whole shared-doc
    closure'
  actor: logan
  at: '2026-09-08'
body_changes:
- mode: append
  reason: 'owner directive given after the 19-hour daemon was killed by hand: the
    daemon must self-terminate after an idle hour, defined by work performed rather
    than by loop iterations'
  actor: logan
  at: '2026-09-07'
  old_length: 3019
  new_length: 4187
evidence:
- tests/test_serve_daemon.py::TestIdleSelfTermination::test_record_useful_work_updates_the_timestamp
- tests/test_serve_daemon.py::TestIdleSelfTermination::test_never_having_worked_is_measured_from_start_time
- tests/test_serve_daemon.py::TestIdleSelfTermination::test_idle_under_one_hour_is_not_terminal
- tests/test_serve_daemon.py::TestIdleSelfTermination::test_idle_over_one_hour_is_terminal
- tests/test_serve_daemon.py::TestIdleSelfTermination::test_loop_self_terminates_after_the_idle_ceiling
- tests/test_serve_daemon.py::TestIdleSelfTermination::test_loop_does_not_terminate_while_work_keeps_happening
designated_repro_test: null
acceptance:
- text: given a serve daemon that has performed no useful work for more than one hour,
    when the liveness check runs, then the daemon terminates itself, and idleness
    is measured by work performed rather than by poll iterations
  evidence:
  - tests/test_serve_daemon.py::TestIdleSelfTermination::test_record_useful_work_updates_the_timestamp
  - tests/test_serve_daemon.py::TestIdleSelfTermination::test_never_having_worked_is_measured_from_start_time
  - tests/test_serve_daemon.py::TestIdleSelfTermination::test_idle_under_one_hour_is_not_terminal
  - tests/test_serve_daemon.py::TestIdleSelfTermination::test_idle_over_one_hour_is_terminal
  - tests/test_serve_daemon.py::TestIdleSelfTermination::test_loop_self_terminates_after_the_idle_ceiling
  - tests/test_serve_daemon.py::TestIdleSelfTermination::test_loop_does_not_terminate_while_work_keeps_happening
acceptance_amendments:
- op: remove
  index: 3
  old_text: given a land whose graph build failed, when it emits its land proof, then
    the proof distinguishes an unmeasured verification caused by an infrastructure
    failure from a genuine skip
  new_text: null
  reason: 'split to T-draft-d015a2a1: the fix lives in src/frob/tickets/_land_verify.py
    + _land.py, outside this ticket''s src/frob/serve/_daemon.py + src/frob/serve/_warm.py
    scope, and is a large enough land-proof-semantics change to deserve its own ticket
    rather than widen this one''s blast radius'
  actor: logan
  at: '2026-09-08'
- op: remove
  index: 2
  old_text: given a graph build that cannot take the cache lock, when it reports the
    failure, then the message names the holding process rather than saying only that
    the database is locked
  new_text: null
  reason: 'split to T-draft-f40f5848: naming the holding process on CacheLocked requires
    editing src/frob/graph/cache.py, outside this ticket''s declared scope'
  actor: logan
  at: '2026-09-08'
- op: remove
  index: 1
  old_text: given a running serve daemon that is idle between polls, when another
    process opens the graph cache, then it acquires the lock and completes its build
    rather than timing out
  new_text: null
  reason: 'split to T-draft-f40f5848: releasing/avoiding the write lock and allowing
    concurrent readers requires editing src/frob/graph/cache.py (journal-mode/transaction-length
    decisions there), outside this ticket''s declared scope -- see that ticket''s
    body for the WAL/T-3644 dead-end investigation and the plausible real mechanism
    (unthrottled re-verify on every main-HEAD move in a busy fleet root) this ticket''s
    own files cannot safely fix without either violating tests/test_serve_daemon.py''s
    bound synchronous-refresh contract or defeating the shared-cache warm-up this
    daemon exists to provide'
  actor: logan
  at: '2026-09-08'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE SERVE DAEMON HOLDS AN EXCLUSIVE WRITE LOCK ON THE GRAPH CACHE FOR ITS ENTIRE
LIFETIME, AND EVERY OTHER PROCESS IN THE REPOSITORY LOSES ITS GRAPH BUILD AS A
RESULT. This is a measured, currently-live fleet outage, not a theoretical race.

WHAT WAS MEASURED, 2026-09-07. A long-running serve process (19 hours old at the
time of measurement) held two write file descriptors on the graph cache database
continuously. Every other frob invocation in the repository failed its graph
build with a lock timeout, emitting first a stale-or-corrupt connection warning,
then a thirty-second give-up, then a build failure. A read-only connection from
a separate interpreter could not even run an integrity check: it was refused
with a plain lock error.

WHY THIS IS WORSE THAN SLOW. The failure is not loud where it matters. A ticket
land whose graph build fails still reports success and simply omits its
verify-queue intent, and its land proof then reads as unmeasured rather than as
failed. That is the silent-zero shape: an absent measurement presented as an
uneventful one. Several lands today recorded skipped verification for exactly
this reason and nothing in their output said the cause was a lock held by
another process.

THERE IS A SECOND, PROBABLY RELATED DEFECT VISIBLE IN THE SAME MEASUREMENT. The
database also reported a malformed disk image on two separate occasions today,
both times under concurrent writers, and both times on this same cache rather
than on any of the other databases beside it. A single long-lived writer plus
opportunistic writers is a plausible mechanism for that, so investigate whether
the corruption and the starvation share a cause before treating them as two
problems.

WHAT A FIX MUST DO. The daemon has no business holding a write lock while idle.
It polls; between polls it should hold nothing. Decide whether the daemon needs
write access at all for the work it actually does, and if it does, make it take
the lock for the duration of a write and release it immediately. Consider also
whether this database should be opened in a mode that permits concurrent readers
alongside a writer, since the read path is what most callers need and it is
currently refused outright.

DIAGNOSABILITY IS PART OF THE FIX. When a graph build loses the lock, the error
should name the process holding it. Today it says only that the database is
locked, which sent this investigation through a corruption hypothesis first;
the holder was found only by inspecting open file descriptors by hand.

A NOTE ON THE STATUS VERB, WORTH FIXING OR SPLITTING SEPARATELY IF IT IS NOT
CHEAP HERE. The daemon status response is currently a single structured payload
of roughly 28,000 lines carrying 4,808 delta entries, and it announces in the
same payload that its baseline is stale. A delta computed against a stale
baseline reports pre-existing findings as new, which is a known false-positive
mechanism in this repository, and a status response that must be paged through
in chunks is not a status response.



OWNER DIRECTIVE, ADDED AFTER THE DAEMON WAS KILLED BY HAND: THE DAEMON MUST HAVE
A LIVENESS CHECK AND TERMINATE ITSELF. More than one hour with nothing to do
means death. The instance measured here had been running for nineteen hours,
its last useful result was seven hours stale, and the session that started it
had gone offline long before; nothing in the system noticed or cared, and the
only thing that ended it was a person reading open file descriptors by hand.

The self-termination requirement stands on its own and is not satisfied by
fixing the lock behaviour. Even a daemon that holds no lock while idle should
not outlive its usefulness by most of a day. Treat the two as separate
obligations on the same component: release the lock between polls, AND exit
after an idle hour.

Define idle by work actually performed, not by whether the process loop ran. A
poll that finds nothing to do is idleness, not activity, or the check will never
fire on precisely the daemon it needs to catch. The instance measured here was
polling every few minutes throughout its nineteen hours; a heartbeat-based
liveness check would have called it healthy the entire time.
