## Done report

Root cause: `fleet_status.py`'s forkserver reporting measured ORPHAN
STATUS and SWAP only (T-2517), never RESIDENT memory -- a fleet of
healthy, live-parented, non-swapping forkservers reads as clean 0/0/0.0GB
across all three existing lines while consuming the host's actual RAM
(measured incident: 12.5GB RSS, 1.2GB available, ORPHANED/STALE/SWAP all
zero). Three reassuring lines outrank one alarming line appended after
them -- the defect was the CHOICE OF METRIC and the ORDER, not an
arithmetic error, per the ticket's own framing.

Built:
1. `forkserver_rss_held_kb` (sums VmRSS across every live forkserver,
   sibling of the existing `forkserver_swap_held_kb`) and `forkserver_
   count` (denominator for attribution).
2. `_forkserver_rss_headline`: a new, ALWAYS-PRINTED line that now LEADS
   the forkserver section (printed before even the T-2818 contradiction
   line) -- "N concurrent check(s) -> M forkserver(s) -> X.XGB resident",
   attributing the aggregate to concurrent checks per the ticket's
   explicit requirement, not just a fourth sub-line. A `WARNING:` clause
   is appended only at/above a 2GB floor (`_FORKSERVER_RSS_WARNING_FLOOR_
   KB`, well below the 12.5GB incident, well above ordinary idle
   footprint) -- the must-fire/must-stay-quiet split the ticket required.
3. Advisory-vs-cap: answered explicitly in `_forkserver_rss_headline`'s
   and `_forkserver_status_lines`'s own docstrings (also mirrored into
   docs/guides/coordinator-scripts.md). CONCURRENT CHECKS stays advisory,
   not a hard cap -- a hard cap would refuse a coordinator's own `frob
   check` at the exact moment they need one most (verifying a land or a
   ticket close) just because the fleet is busy. T-2473 chose advisory
   for that reason and the incident does not change it: the incident was
   a coordinator not SEEING the RSS consequence, not being unable to stop
   once warned. The CONCURRENT CHECKS line itself now points back at the
   RSS headline for its own cost, per the ticket's own alternative-3
   option.

Filed: none.

Gates: `frob check --ticket T-3407` clean of new findings -- remaining
errors are pre-existing repo-wide (DEPR006/WAIVE011 lock-producer
staleness, T-3410/T-3411 unrelated ticket findings, TICK004 rot warnings,
DRIFT001 in _rapid_sweep.py, LARGE001/OPAQUE001/SELFAUDIT001 in unrelated
files), none touching this ticket's scope. `frob test --base main` pass
(16 outcomes, exit=0); node-id pytest -p no:xdist on
tests/unit/test_coordinator_scripts.py (full file, 249 tests): all pass,
0 failed. Designated repro (`--designate-repro`) confirmed FAILED_AT_
PARENT against a test-only commit predating the fix.

### Changed
```
 docs/guides/coordinator-scripts.md     |  71 ++++++++++
 scripts/fleet_status.py                | 247 ++++++++++++++++++++++++++++++---
 tests/unit/test_coordinator_scripts.py | 115 +++++++++++++++
 tickets/T-3407/ticket.md               |  29 +++-
 4 files changed, 438 insertions(+), 24 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestForkserverRssHeldKb::test_sums_vmrss_across_every_forkserver` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestForkserverRssHeldKb::test_missing_status_file_degrades_that_entry_to_zero_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestForkserverRssHeldKb::test_missing_proc_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestForkserverCount::test_counts_every_live_forkserver` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestForkserverCount::test_missing_proc_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestForkserverRssHeadline::test_large_rss_produces_a_visible_warning` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestForkserverRssHeadline::test_small_rss_stays_quiet` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestForkserverRssHeadline::test_unknown_inputs_degrade_to_unknown_not_zero` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 10 error(s), 4156 warning(s), 858 waived
- error-findings: COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
