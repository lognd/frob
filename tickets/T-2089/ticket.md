---
id: T-2089
title: frob ticket doable's T-2006 sweep-candidate revalidation spawns an uncached
  full check (207.5s measured)
state: done
kind: feature
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_second_call_same_tree_reuses_cache_no_second_spawn
- tests/unit/test_rapid_sweep.py::TestTreeStateKey::test_non_repo_is_none
- tests/unit/test_rapid_sweep.py::TestTreeStateKey::test_real_repo_returns_a_key
- tests/unit/test_rapid_sweep.py::TestTreeStateKey::test_dirty_tree_changes_the_key
- tests/unit/test_rapid_sweep.py::TestRevalidationCache::test_absent_cache_is_none
- tests/unit/test_rapid_sweep.py::TestRevalidationCache::test_corrupt_cache_is_none
- tests/unit/test_rapid_sweep.py::TestRevalidationCache::test_write_then_read_round_trips
- tests/unit/test_rapid_sweep.py::TestRevalidationCache::test_mismatched_tree_key_is_none
- tests/unit/test_rapid_sweep.py::TestRevalidationCache::test_mismatched_pairs_is_none
- tests/unit/test_rapid_sweep.py::TestRevalidationCache::test_expired_ttl_is_none
designated_repro_test: tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_second_call_same_tree_reuses_cache_no_second_spawn
threat: null
component: null
labels:
- perf
anchor: false
anchor_reason: null
land_commit: null
---
## Measured (while working T-2078, not fixed here per that ticket's own brief)

`revalidate_dispatchable_sweep_tickets` (src/frob/app/ticket_runner/_rapid_sweep.py,
T-2006) is called from `frob ticket doable`'s own render path on EVERY
`doable` invocation, unconditionally, whenever the queue holds at least
one sweep-filed candidate ticket (`_parse_sweep_ticket_identities`
resolves for it). It has no cache and no TTL: each call spawns a fresh,
independent, FULL `frob check --budget <N> --json` subprocess
(`_spawn_true_count_check`) and only filters the result down to the
candidate identities AFTER the full run completes
(`_matching_error_diagnostics`) -- the budget/scope narrowing happens on
the OUTPUT, not the check itself, so the spawn cost is the same as an
ordinary full `frob check --budget` run regardless of how few identities
are actually being re-verified.

One real invocation logged:

    rapid sweep: T-2006: doable-time re-verification of 21 sweep-filed
    candidate ticket(s) (265 total identit(ies)) took 207.5s

`frob ticket doable` is a QUERY verb -- read-only, run routinely by both
humans and coordinators to pick the next unit of work, often several
times in a session with the tree unchanged in between. 207.5s is
comparable to `frob ticket land`'s own ~210s land-lock cost (the current
fleet-wide throughput ceiling per this session's brief), so a query verb
paying nearly the same price as a write verb, repeatedly, for a tree
that has not moved, is a real throughput problem on its own.

## Is it cacheable or deferrable? (measured, not assumed)

Cacheable: yes, in the straightforward sense. The check result depends
only on the tree state (HEAD sha / working-tree digest) and the budget
requested -- nothing else varies between two `doable` calls against the
same commit. There is already a precedent for exactly this shape
elsewhere in this file (`.frob/check-budget-timing.json`'s rolling
per-stage-group estimate, and the digest-keyed gate-result cache T-1346
turned on by default for `frob check` itself generally) -- but this
specific spawn bypasses both: it is a raw subprocess call, not a
same-process `run_gates` call, so T-1346's cache never sees it, and nothing
memoizes the SUBPROCESS's own result across repeated `doable` calls at
the same tree state.

Deferrable: also plausible. `revalidate_dispatchable_sweep_tickets`'s own
docstring already frames its reason for existing as closing the window
between "identities got fixed" and "the next unrelated land's sweep"
happens to catch it -- but that window does not require re-checking on
EVERY `doable` call; a short TTL (e.g. re-use a result from the last N
minutes / same HEAD sha) would still close the same window while cutting
the common case (several `doable` calls in a row, tree unchanged) to one
real spawn.

Not measured here: which of the two (result cache keyed on tree digest,
or a TTL) is the better fit, or the actual current call frequency of
`doable` in a busy session (needed to size the real savings). That is
follow-up work for whoever picks this up, not assumed in this filing.

## Scope

Fix belongs in `frob.app.ticket_runner._rapid_sweep`
(`_spawn_true_count_check`/`revalidate_dispatchable_sweep_tickets`) plus
its own test file `tests/unit/test_rapid_sweep.py`. Filed as a `perf`
ticket per this session's brief -- investigation only, not implemented
here; T-2078 (which found this) stays scoped to its own transition-
ordering fix.

## Done report

Changed:
- src/frob/app/ticket_runner/_rapid_sweep.py::_tree_state_key (new)
- src/frob/app/ticket_runner/_rapid_sweep.py::_revalidation_cache_path (new)
- src/frob/app/ticket_runner/_rapid_sweep.py::_read_revalidation_cache (new)
- src/frob/app/ticket_runner/_rapid_sweep.py::_write_revalidation_cache (new)
- src/frob/app/ticket_runner/_rapid_sweep.py::_reproducing_identities_cached (new, ARCH001 split)
- src/frob/app/ticket_runner/_rapid_sweep.py::revalidate_dispatchable_sweep_tickets (now calls the cache)

Measured before implementing, per this ticket's own brief: the spawn is
content-cacheable (result depends only on tree state + budget, nothing
else varies between calls) and the window T-2006 exists to close does
not require re-checking on every single `doable` call -- a cache keyed
on exact tree state closes the same window while cutting the common
case (several `doable` calls in a row, tree unchanged) to one real
spawn. Implemented a tree-state-keyed cache (HEAD sha + a cheap
`git status --porcelain` dirty signal, never a full-content hash) plus
the exact identity set re-checked, with a 300s TTL as defense-in-depth
on top of the content key. A cache-unavailable signal (non-repo, git
spawn failure) degrades to the prior uncached behavior, never to a
false HIT -- an unmeasured candidate is never reported as clean.

Evidence:
- tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_second_call_same_tree_reuses_cache_no_second_spawn
  (the repro: proves exactly ONE spawn across two calls against an
  unchanged tree; genuinely FAILED_AT_PARENT at the test-only commit
  473344c14, confirmed via `frob ticket evidence --check-repro`)
- tests/unit/test_rapid_sweep.py::TestTreeStateKey.test_non_repo_is_none
- tests/unit/test_rapid_sweep.py::TestTreeStateKey.test_real_repo_returns_a_key
- tests/unit/test_rapid_sweep.py::TestTreeStateKey.test_dirty_tree_changes_the_key
- tests/unit/test_rapid_sweep.py::TestRevalidationCache.test_absent_cache_is_none
- tests/unit/test_rapid_sweep.py::TestRevalidationCache.test_corrupt_cache_is_none
- tests/unit/test_rapid_sweep.py::TestRevalidationCache.test_write_then_read_round_trips
- tests/unit/test_rapid_sweep.py::TestRevalidationCache.test_mismatched_tree_key_is_none
- tests/unit/test_rapid_sweep.py::TestRevalidationCache.test_mismatched_pairs_is_none
- tests/unit/test_rapid_sweep.py::TestRevalidationCache.test_expired_ttl_is_none

Gates: `frob check --ticket T-2089 --only test --only archgate --only
coverage --only sys` clean (FROB_NO_GATE_CACHE=1 re-measure of
archgate+drift also clean -- ARCH001 initially fired at 96 lines on the
combined cache-wiring; split out `_reproducing_identities_cached` to
bring `revalidate_dispatchable_sweep_tickets` back under the 60-line
threshold, verified 0 errors after). `frob check --land-parity` clean
(0 unscoped errors).

While verifying, found a pre-existing, order-dependent flaky pair in
this SAME test class -- `test_fully_resolved_candidate_is_dropped` and
`test_terminal_ticket_is_not_selected_and_logs_no_invalid_transition`
intermittently interfere when run together despite independent
`tmp_path` fixtures. Confirmed this predates T-2089's own change (5
repeated runs at the parent commit 0aeffe33a: 2 clean, 3 failed,
different member each time) -- not implemented/investigated further
here, out of this ticket's perf/caching scope.

Filed: T-2100 (the pre-existing flaky-test-pair finding above)

### Changed
```
 src/frob/app/ticket_runner/_rapid_sweep.py | 206 +++++++++++++++++++++++++++--
 tests/unit/test_rapid_sweep.py             | 148 +++++++++++++++++++++
 tickets/T-2089/done-report.md              |  82 ++++++++++++
 tickets/T-2089/ticket.md                   |  15 ++-
 tickets/T-draft-0251e7fb/ticket.md         |  63 +++++++++
 5 files changed, 502 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_second_call_same_tree_reuses_cache_no_second_spawn` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestTreeStateKey::test_non_repo_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestTreeStateKey::test_real_repo_returns_a_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestTreeStateKey::test_dirty_tree_changes_the_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRevalidationCache::test_absent_cache_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRevalidationCache::test_corrupt_cache_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRevalidationCache::test_write_then_read_round_trips` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRevalidationCache::test_mismatched_tree_key_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRevalidationCache::test_mismatched_pairs_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRevalidationCache::test_expired_ttl_is_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: PRE001@tickets/T-2089
