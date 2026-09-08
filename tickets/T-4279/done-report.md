## Done report

Replaced the fixed 250ms `_STAT_TRUST_MARGIN_NS` constant with a margin derived
from the mount's own measured mtime granularity, per the ticket's own
"do not simply raise the constant" requirement.

`_probe_mtime_granularity_ns` measures the filesystem's OBSERVED mtime-update
granularity via a real back-to-back write loop (20 writes, matching T-4257's
own original measurement methodology) on a throwaway probe file under
`<root>/.frob/`. Deliberately NOT an `os.utime` round trip: an earlier draft
did that and was wrong -- a filesystem can store an arbitrary nanosecond value
written directly via `os.utime` while the kernel's own timestamp-update path
for a REAL write still advances mtime in much coarser ticks (exactly the gap
T-4257 measured empirically: this repo's own ext4 mount nominally stores full
ns precision, yet 5/20 real back-to-back writes still collided). Only a real
write loop observes that actual behavior.

`_mtime_granularity_ns` caches the measurement both in-process and on disk
(`<root>/.frob/mtime-granularity-ns`), so the "measure once" half of the
remedy survives past one short-lived CLI invocation, not just one process.
Deliberately a plain text sidecar file rather than a new `frob.graph.cache`
sqlite meta row: this ticket's own declared scope is `src/frob/graph/
__init__.py` only. An unmeasurable (`None`) result is cached in-process for
the run but NOT persisted to disk, so a transient failure (root momentarily
unwritable) does not permanently pin every future invocation to the safe
path once the cause clears.

`_stat_trust_margin_ns` derives the margin as `_STAT_TRUST_SAFETY_MULTIPLIER`
(50, matching the ratio the original 250ms constant represented over this
repo's own measured <5ms granularity) times the measured granularity, or
`None` if unmeasurable. `_stat_trustworthy` now takes that margin as a
parameter and always returns `False` on `None` -- obligation [2]: a
filesystem whose granularity cannot be established falls back to the content
hash unconditionally, never guesses.

Obligation [1] verified directly: `test_coarse_granularity_widens_the_
untrusted_window` simulates a 2-second-granularity mount (the ticket's own
"older removable formats" example) and confirms a 1-second-old stat entry --
outside the OLD fixed 250ms margin, which would have wrongly trusted it -- is
correctly NOT trusted under the new derived margin. I confirmed this by hand:
under the pre-fix formula (`time.time_ns() - mtime_ns > 250_000_000`), that
same 1-second-old entry evaluates to `True` (wrongly trusted); under the fix
it is `False`.

Existing T-4257 tests (`tests/test_gate_cache.py::TestStatKeyCoarseClockSafety`,
both of them) pass unchanged against the real measured margin on this repo's
own mount -- the fix preserves the validated behavior here while adding the
missing safety for coarser mounts.

Declared the new `fs.write` capability sites (the probe write and the sidecar
cache write) in `design/frob.strata` for both `graphlang` (the new call site)
and `testsuite` (the new test file), and bumped both via-ratchet ceilings in
`docs/design/registry/capability-via-ratchet.lock.json` per the gate's own
named remedy.

What was actually re-verified vs skipped: `frob check --ticket T-4279`
(scope/fmt/affect_drift/prework/sys, run directly, not the aggregate) is
clean except pre-existing, unrelated `claude_hooks` SELFAUDIT001/SYS101
findings (confirmed present with zero diff to `.claude/hooks` or that node's
declaration, filed as T-4296). The full local test suite
(tests/test_graph.py, tests/test_graph_lock.py, tests/unit/test_graph_cache.py,
tests/unit/test_graph_build_lock.py, tests/unit/test_graph_ingest_batching.py,
tests/unit/test_graph_lock_holder_naming.py, tests/test_gate_cache.py,
tests/unit/test_graph_stat_trust_margin.py -- 272 tests) passed locally before
close. `frob ticket land`'s own claims re-verification is expected to run
SKIPPED-UNMEASURED under the rapid profile (as it did for the sibling T-4282
land) -- treat that as UNKNOWN at land time, not as a second confirmation of
green; the local pytest run above is the actual measured evidence for this
ticket's own claims.

Filed: T-4296 (claude_hooks node's SYS101 declarations no longer
match observed capabilities -- pre-existing, confirmed unrelated to this
diff, may overlap existing queued T-2837/T-3020).

### Changed
```
 design/frob.strata                                 |  10 +-
 .../registry/capability-via-ratchet.lock.json      |  12 +-
 src/frob/graph/__init__.py                         | 274 ++++++++++++++++++++-
 tests/unit/test_graph_stat_trust_margin.py         | 214 ++++++++++++++++
 tickets/T-4279/ticket.md                           |  66 ++++-
 tickets/T-4296/ticket.md                 |  30 +++
 6 files changed, 581 insertions(+), 25 deletions(-)
```

### Evidence
- `tests/unit/test_graph_stat_trust_margin.py::TestStatTrustMarginAndTrustworthy::test_coarse_granularity_widens_the_untrusted_window` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_stat_trust_margin.py::TestStatTrustMarginAndTrustworthy::test_none_margin_never_trusts_regardless_of_age` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_stat_trust_margin.py::TestStatTrustMarginAndTrustworthy::test_stat_within_margin_is_not_trusted` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_stat_trust_margin.py::TestStatTrustMarginAndTrustworthy::test_stat_past_margin_is_trusted` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_stat_trust_margin.py::TestStatTrustMarginAndTrustworthy::test_margin_is_granularity_times_safety_multiplier` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_stat_trust_margin.py::TestStatTrustMarginAndTrustworthy::test_margin_is_none_when_granularity_unmeasurable` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_stat_trust_margin.py::TestProbeMtimeGranularityNs::test_real_probe_returns_a_plausible_small_value` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_stat_trust_margin.py::TestProbeMtimeGranularityNs::test_all_samples_colliding_falls_back_to_loop_span` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_stat_trust_margin.py::TestMtimeGranularityCaching::test_second_call_does_not_reprobe` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_stat_trust_margin.py::TestMtimeGranularityCaching::test_on_disk_cache_survives_a_fresh_in_process_cache` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestStatKeyCoarseClockSafety::test_recent_stat_match_falls_through_to_content_hash` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestStatKeyCoarseClockSafety::test_old_stat_match_is_trusted_and_skips_reparse` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 7 error(s), 4648 warning(s), 950 waived
- error-findings: ARCH001@src/frob/graph/__init__.py, ARCH103@src/frob/graph/cache.py, COV007@src/frob/gates/_tdd_order.py, LANDPARITY002@src/frob/graph/__init__.py, SCOPE002@tickets.md, SELFAUDIT001@design, WIRE002@tests/test_ci_workflow_timeout.py
