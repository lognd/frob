---
id: T-2165
title: T-2089's doable-revalidation cache keys on whole-tree state, too narrow to
  hit under concurrent-land load
state: done
kind: feature
origin: human
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
evidence_scope:
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: 'probe: same-glob no-op to check lease status'
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_rapid_sweep.py::TestIdentityScopedStateKey::test_unchanged_files_same_key_across_a_head_move
- tests/unit/test_rapid_sweep.py::TestIdentityScopedStateKey::test_editing_a_named_file_changes_the_key
- tests/unit/test_rapid_sweep.py::TestIdentityScopedStateKey::test_editing_an_unrelated_file_does_not_change_the_key
- tests/unit/test_rapid_sweep.py::TestIdentityScopedStateKey::test_uncommitted_edit_to_a_named_file_changes_the_key
- tests/unit/test_rapid_sweep.py::TestIdentityScopedStateKey::test_missing_file_has_a_stable_sentinel_digest
- tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_second_call_same_tree_reuses_cache_no_second_spawn
- tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_cache_hits_across_a_head_move_when_candidate_files_are_unchanged
- tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_uncommitted_edit_to_candidate_file_still_forces_a_respawn
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2106 bounded the doable-time re-verification's own budget (300s ->
20s), fixing the measured 736s -> 86.5s throughput problem. Separately,
during that investigation, T-2089's own tree-state-keyed cache
(revalidate_dispatchable_sweep_tickets -> _reproducing_identities_cached
-> _tree_state_key, src/frob/app/ticket_runner/_rapid_sweep.py) was
confirmed CORRECTLY WIRED, not dead: it hashes the committed HEAD sha
plus a digest of `git status --porcelain`'s output
(src/frob/app/ticket_runner/_rapid_sweep.py::_tree_state_key).

The problem is what it keys on, not whether it fires. In a busy
multi-agent session HEAD advances on essentially every land (a handful
of minutes apart, sometimes less), so two `frob ticket doable` calls
made by the SAME coordinator a minute apart, against a tree that is
IDENTICAL from the sweep-revalidation's own point of view (no file the
revalidated identities' rules/files touch has changed), still get
different tree_key values and the cache cannot hit. Confirmed live in
this session's own AFTER measurement (T-2106's Done report): the
doable-time re-verification reported UNMEASURABLE (timed out) rather
than served from cache, on a tree that had almost certainly not moved
relative to the CANDIDATE files being revalidated.

Proposed direction (not implemented -- this is a genuine design
question, not a blind widen): key the cache on something closer to
"has anything relevant to THESE specific (rule, file) identities
changed" rather than "has the whole tree's HEAD+status changed at
all" -- e.g. the mtime/content-hash of just the files named in
`all_pairs`, or a cheap git-log-since-cache-write check restricted to
those paths. Widening naively to "same HEAD, ignore status" would be
UNSOUND (an agent's own uncommitted fix to one of the revalidated
files must not be masked by a stale cache) -- the narrowing has to be
identity-scoped, not blanket-relaxed. This needs the same "does not
mask a genuine fix" care T-1436's gate-cache staleness bug already
paid for in gate:CHECK's own cache; a naive widen risks reintroducing
exactly that failure mode in this cache instead.