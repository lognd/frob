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