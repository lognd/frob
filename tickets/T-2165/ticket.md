---
id: T-2165
title: T-2089's doable-revalidation cache keys on whole-tree state, too narrow to
  hit under concurrent-land load
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
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
