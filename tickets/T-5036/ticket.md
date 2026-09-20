---
id: T-5036
title: Cache repo_root to stop O(tickets x holders) git subprocess spawns in doable()
state: done
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: T-4806
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gitio.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_gitio.py::TestRepoRoot::test_memoized_per_start
designated_repro_test: null
acceptance:
- text: repo_root(start) is memoized per resolved start path for the process lifetime
    (no re-spawn of git on a cache hit), verified by test_memoized_per_start
  evidence:
  - tests/test_gitio.py::TestRepoRoot::test_memoized_per_start
acceptance_amendments:
- op: replace
  index: 1
  old_text: test_real_repo_ledger_is_tick008_clean passes on Windows within its timeout
  new_text: repo_root(start) is memoized per resolved start path for the process lifetime
    (no re-spawn of git on a cache hit), verified by test_memoized_per_start
  reason: 'narrowed from the original ''test_real_repo_ledger_is_tick008_clean completes
    well within its Windows CI timeout'' criterion: diagnosis during this ticket found
    the Windows TICK008 stall has a SECOND, larger root cause (same_worktree_lease''s
    own uncached read_all_leases rescan, filed separately as T-5075) that this ticket''s
    fix alone does not resolve -- rewriting to what this ticket''s own change actually
    proves, rather than leaving an unproven criterion or mis-binding evidence to it'
  actor: logan
  at: '2026-09-19'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Windows CI (run 35476139324) stalls past 600s in tests/gates_suite/test_tick.py TestTick008UnknownLedgerFields test_real_repo_ledger_is_tick008_clean. Reproduced locally via winrun with faulthandler: the hang is in tickets_gate -> _tick007_undispatched_stale -> doable() -> leased_by() -> _leased_by_one_holder() -> frob.tickets._leases.same_worktree_lease() -> frob.gitio.repo_root(root) -> a fresh git rev-parse --show-toplevel subprocess spawn, EVERY SINGLE TIME, with no caching. same_worktree_lease is called once per (ticket, holder) pair inside leased_by's inner loop over all_leases, and leased_by runs once per ticket inside doable()'s main loop -- against this repo's live ~1171-ticket queue this is on the order of hundreds of thousands of repo_root() calls, ALL resolving the exact same, unchanging root path within one doable() invocation. Each spawns a real git subprocess; process spawn is orders of magnitude more expensive on Windows than POSIX fork, so what is merely slow on Linux/macOS (masking the bug there) stalls past any CI timeout on Windows. This is the same class of unbounded per-candidate-x-holder-pair perf bug T-0453/T-0773 already fixed for scope_breadth_context/_all_leases in frob.tickets._doable -- same_worktree_lease's own repo_root call was missed by that precedent. Fix: memoize frob.gitio.repo_root (e.g. functools.lru_cache keyed by the resolved start path string, or a module-level dict cache) so repeated calls for the same start path within one process resolve once. Verify via winrun (~/bin/winrun) with faulthandler after the fix -- one clean run does not prove an intermittent fix, so also spot-check the stall no longer reproduces under repeated runs if time allows.