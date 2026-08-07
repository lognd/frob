## Done report

Implemented the deferred T-0476 lease reconcile (audit M2): read_all_leases
now opportunistically unlinks a lease file once its worktree's absence is
CONFIRMED, and prunes the matching stat-cache entry so the cache never
leaks the removed path. Added a recorded_at TTL (LEASE_TTL_SECONDS, 6
hours, module constant in _leases.py) via two new public helpers,
lease_age_seconds and is_lease_ttl_expired, for the live-path-but-dead-
agent case read_all_leases' path check alone cannot catch.
frob.serve._daemon._worktree_branches now filters TTL-expired leases
before poll_rebase_bot re-simulates them, logging the skip once per
(root, ticket id) via a new _ttl_skip_logged set, mirroring _leases.py's
existing log-once pattern.

Reviewer round 1 (REJECT): the original guard used a plain
Path(record.worktree).exists() boolean, which swallows every OSError --
a transient stat failure (PermissionError, a stale NFS handle, a slow
mount, T-0584) reads identically to a genuine ENOENT and would have
silently unlinked a perfectly LIVE peer's lease (audit L2's TOCTOU note).
Fixed by replacing it with _probe_worktree_liveness: os.stat on the
worktree path, catching FileNotFoundError as the ONLY trustworthy
absence signal, and additionally requiring the PARENT directory to
still stat successfully (so a wholesale mount failure can never read as
a single worktree's absence). Any other OSError is classified
"ambiguous" -- the lease is skipped for this pass exactly as before (not
promoted to live), logged once via a new _ambiguous_liveness_logged set,
but never unlinked. Only "confirmed_absent" (FileNotFoundError + a
reachable parent) triggers the opportunistic unlink. Added
TestAmbiguousLivenessGuard (3 tests: ambiguous stat failure does not
unlink, ambiguous failure logs once, genuine ENOENT still unlinks) to
tests/test_tickets_leases.py, and updated the read_all_leases docstring
and inline comments to describe the real guard instead of the
overstated "re-verify non-existence" language from round 1.

Scope extended by one file (frob ticket scope T-0782 --add
tests/test_serve_daemon.py) because the ticket's own acceptance criteria
require a daemon-path regression test that necessarily lives in that
module.

### Changed
```
 src/frob/serve/_daemon.py    |  55 ++++++++++-
 src/frob/tickets/_leases.py  | 219 ++++++++++++++++++++++++++++++++++++++-----
 tests/test_serve_daemon.py   |  55 +++++++++++
 tests/test_tickets_leases.py | 189 +++++++++++++++++++++++++++++++++++++
 tickets.md                   |  63 ++++++++++++-
 5 files changed, 549 insertions(+), 32 deletions(-)
```

### Evidence
- `tests/test_tickets_leases.py::TestLeaseTtl::test_age_seconds_computes_elapsed_time` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseTtl::test_age_seconds_none_for_unparseable_timestamp` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseTtl::test_expired_past_ttl` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseTtl::test_not_expired_within_ttl` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseTtl::test_unparseable_timestamp_is_never_treated_as_expired` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestOpportunisticUnlink::test_stale_path_lease_is_unlinked_from_disk` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestOpportunisticUnlink::test_live_lease_is_never_unlinked` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestPollRebaseBot::test_ttl_expired_lease_skipped_and_logged_once` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestAmbiguousLivenessGuard::test_ambiguous_stat_failure_does_not_unlink` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestAmbiguousLivenessGuard::test_ambiguous_failure_is_logged_once_per_process` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestAmbiguousLivenessGuard::test_genuine_enoent_still_unlinks` (pytest node id, verified passing when recorded)
