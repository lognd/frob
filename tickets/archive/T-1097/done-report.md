## Done report

Generalized T-0322/T-1095's coverage-only fcntl.flock single-flight into
a named resource lease/semaphore primitive the T-1092 socket daemon
itself owns and arbitrates, with release tied to socket connection
liveness.

src/frob/serve/_leases.py (new): `ResourceLeaseManager` -- a
threading.Condition-guarded dict of named resources, each with a fixed
capacity (default `DEFAULT_LEASE_CAPACITY` = 1, an exclusive writer lock,
matching coverage's own contract), created on first mention.
`acquire(resource, holder_id, capacity=, timeout_s=)` blocks until a slot
frees or the timeout elapses (re-entrant for a holder that already holds
the slot, so a redundant acquire from the same connection can't
self-deadlock); `release` frees one slot; `release_holder` frees every
slot a given holder occupies in one call.

src/frob/serve/_socketd.py: two new JSON-RPC methods special-cased in
`_RequestHandler.handle` alongside subscribe/frob_version/frob_shutdown:
`frob_lease_acquire` (blocks THIS connection's own handler thread --
ThreadingUnixStreamServer gives each connection its own thread, so
blocking here never blocks another connection) and `frob_lease_release`.
Each connection gets a `_lease_holder_id` in `setup()`; `handle`'s
`finally` block now unconditionally calls `lease_manager.release_
holder(self._lease_holder_id)`, same place `subscribe`'s per-connection
unsubscribe already runs -- a crashed or killed client (socket closed
with no explicit frob_lease_release) has every lease it held freed the
moment the daemon notices, no daemon restart required (acceptance [1]).
`_DaemonServer.__init__` now constructs one `ResourceLeaseManager` shared
across every connection thread.

tests/test_serve_leases.py: `TestResourceLeaseManager` covers the pure
manager directly (blocking/release, timeout, multi-resource independence,
re-entrancy, release-of-unheld no-op). `TestLeaseRpc.test_second_client_
blocks_until_first_releases` runs two REAL persistent socket connections
against a real running daemon and proves exactly one holds "coverage" at
a time, the second blocks until the first explicitly releases (acceptance
[0]). `TestConnectionCrashReleasesLease.test_closing_connection_without_
explicit_release_frees_the_lease` acquires the lease on one connection,
closes that socket with NO release sent (a real crash-shaped event), and
proves a second client can then acquire it (acceptance [1]).

Scope note (disclosed, not silently dropped): this ticket ships and
proves the daemon-owned arbitration primitive itself. It does NOT rewire
frob.testing._coverage_wait.run_coverage_wait's actual subprocess flow to
acquire ITS lock through this daemon RPC instead of its existing
per-worktree (T-0322) and shared-per-digest (T-1095) fcntl.flock layers
-- that wiring touches frob.app._daemon_proxy, contended with T-1106's
own src/frob/app/ work this wave and outside this ticket's src/frob/
serve/**, src/frob/testing/** scope. Filed as a follow-on:
T-1118.

Also filed (pre-existing, unrelated, found while re-running gates on
this ticket): T-1119 -- gate:TICK006 phantom-draft-citation
errors from T-1077/T-1084's (and, this session, T-1095's own) Done
reports citing drafts a later tickets.md ledger-restore step wiped
before land; a repeat of the historical T-0707/T-0615 incident class the
playbook's section 10b step 6 warns about, hit again despite following
the recipe (the draft in question was filed BEFORE this session's own
restore step for T-1095, not after -- exactly the ordering mistake
section 10b step 6 calls out). Not fixed inline; same disposition as the
pre-existing T-1077/T-1084 instances.

### Changed
```
 docs/modules/serve.md      |  64 ++++++++++++
 src/frob/serve/_leases.py  | 201 +++++++++++++++++++++++++++++++++++
 src/frob/serve/_socketd.py |  64 ++++++++++++
 tests/test_serve_leases.py | 255 +++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                 |  69 +++++++++++-
 5 files changed, 651 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_serve_leases.py::TestResourceLeaseManager::test_second_acquire_blocks_until_first_releases` (pytest node id, verified passing when recorded)
- `tests/test_serve_leases.py::TestResourceLeaseManager::test_acquire_times_out_if_never_freed` (pytest node id, verified passing when recorded)
- `tests/test_serve_leases.py::TestResourceLeaseManager::test_release_holder_frees_every_resource_that_holder_held` (pytest node id, verified passing when recorded)
- `tests/test_serve_leases.py::TestResourceLeaseManager::test_distinct_resources_do_not_contend` (pytest node id, verified passing when recorded)
- `tests/test_serve_leases.py::TestResourceLeaseManager::test_reentrant_acquire_by_same_holder_does_not_deadlock` (pytest node id, verified passing when recorded)
- `tests/test_serve_leases.py::TestResourceLeaseManager::test_release_of_unheld_resource_is_a_noop` (pytest node id, verified passing when recorded)
- `tests/test_serve_leases.py::TestLeaseRpc::test_explicit_release_frees_the_slot_for_the_next_waiter` (pytest node id, verified passing when recorded)
- `tests/test_serve_leases.py::TestLeaseRpc::test_second_client_blocks_until_first_releases` (pytest node id, verified passing when recorded)
- `tests/test_serve_leases.py::TestConnectionCrashReleasesLease::test_closing_connection_without_explicit_release_frees_the_lease` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
