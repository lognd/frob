---
id: T-1454
title: T-1346 gate cache serves stale DRIFT001 result across a frob ack boundary
state: done
kind: bug
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_gate_cache.py
- src/frob/gates/__init__.py
- docs/modules/gates.md
- tests/test_gate_cache.py
- docs/modules/serve.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: fix requires wiring side-channel (lock/coverage/tests/rules/diff/queue)
    digests into extra_key at the _cacheable_gate_call call sites, which live in __init__.py
    alongside _CACHEABLE_GATES itself
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/modules/gates.md
  reason: docs move with the cache-key fix; regression tests live in the module's
    existing test file
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_gate_cache.py
  reason: docs move with the cache-key fix; regression tests live in the module's
    existing test file
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/modules/serve.md
  reason: 'AFFECT001: model_side_channel_key''s frob:doc anchor targets serve.md''s
    T-0602 section; that section must record the T-1454 fix'
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_gate_cache.py::TestSideChannelKey::test_model_side_channel_key_changes_on_field_edit
- tests/test_gate_cache.py::TestSideChannelKey::test_model_side_channel_key_stable_for_equal_content
- tests/test_gate_cache.py::TestRunGatesUseCache::test_ack_invalidates_cached_drift001
designated_repro_test: null
threat: null
component: null
---
Found while working T-1436 (unrelated to that ticket's own scope).

T-1346's dependency-tracked gate cache (use_cache=True, now ON by default
for every `frob check` call, src/frob/check/_python.py::_gate_cache_enabled)
serves a STALE gate:DRIFT/DRIFT001 result across a `frob ack` boundary.

Reproduced directly: after editing a symbol's body and running
`frob ack <ref>` (confirmed frob.lock's on-disk digest for that symbol now
matches the live source digest -- verified both via a direct `build_graph`+
`load_lock`+`drift()` call, which reports 0 stale, AND by inspecting
frob.lock's own JSON), `frob check --only drift` (default cache-enabled
path) still reports DRIFT001 "digest moved since ack" for that exact
symbol. `frob check --only drift` with `FROB_NO_GATE_CACHE=1` set
immediately reports 0 errors/0 violations against the identical
frob.lock/source state -- proving the non-cached path is correct and the
cached path is wrong.

Likely cause: `_gate_cache`'s per-gate dependency tracking for "drift"
(one of `_CACHEABLE_GATES`, src/frob/gates/__init__.py) keys its cached
result off the SOURCE snapshot's digests but not off `frob.lock`'s own
content/mtime -- so a `frob ack` that changes only frob.lock (not any
tracked source file) does not invalidate the cached DRIFT001 finding from
before the ack, and the stale finding is served indefinitely (observed
surviving a `git commit`, an `.frob/cache.db` full rebuild via `rm -f
.frob/cache.db && frob graph build`, and multiple repeat `frob check`
invocations in the same session -- the cache entry itself is what is
stale, not the graph cache).

Impact: any agent following the standard `frob ack <ref>` recipe after a
docstring/body edit will see a *false* DRIFT001 the very next default
`frob check` unless they know to pass `FROB_NO_GATE_CACHE=1` -- which is
undocumented in the agent playbook and easy to mistake for a real,
unresolved drift finding.