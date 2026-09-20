---
id: T-4688
title: 'graph is rebuilt 5+ times per ticket close-out: --only checks share no cache,
  docptr always cold-rebuilds'
state: done
kind: bug
origin: human
created: '2026-09-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/__init__.py
- src/frob/gates/_prework.py
- src/frob/app/coverage_runner.py
- src/frob/app/dup_runner.py
- src/frob/app/ack_runner.py
- src/frob/app/graph_runner.py
- docs/modules/graph*.md
- tests/unit/test_app_runners_batch5.py
- tests/unit/test_graph_get_snapshot.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/__init__.py
  reason: in-progress leases held by T-3962/T-3995/T-4112/T-4113/T-4212; deferring
    those call sites to avoid collision
  actor: logan
  at: '2026-09-19'
- op: remove
  glob: src/frob/app/check_runner.py
  reason: in-progress leases held by T-3962/T-3995/T-4112/T-4113/T-4212; deferring
    those call sites to avoid collision
  actor: logan
  at: '2026-09-19'
- op: remove
  glob: src/frob/app/sys_runner.py
  reason: in-progress leases held by T-3962/T-3995/T-4112/T-4113/T-4212; deferring
    those call sites to avoid collision
  actor: logan
  at: '2026-09-19'
- op: remove
  glob: src/frob/gates/_sys.py
  reason: in-progress leases held by T-3962/T-3995/T-4112/T-4113/T-4212; deferring
    those call sites to avoid collision
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/test_app_runners_batch5.py
  reason: test fixture updates required by get_snapshot migration (T-draft-ea93df7b);
    new test file since tests/test_graph.py is leased by in-progress T-4625
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/test_graph_get_snapshot.py
  reason: test fixture updates required by get_snapshot migration (T-draft-ea93df7b);
    new test file since tests/test_graph.py is leased by in-progress T-4625
  actor: logan
  at: '2026-09-19'
evidence:
- tests/unit/test_graph_get_snapshot.py::TestGetSnapshot::test_second_call_on_unchanged_tree_does_not_rebuild
- tests/unit/test_graph_get_snapshot.py::TestGetSnapshot::test_changed_file_triggers_exactly_one_rebuild
- tests/unit/test_graph_get_snapshot.py::TestGetSnapshot::test_load_failure_falls_back_to_build
designated_repro_test: null
acceptance:
- text: two consecutive get_snapshot calls on an unchanged tree build the graph zero
    additional times on the second call
  evidence:
  - tests/unit/test_graph_get_snapshot.py::TestGetSnapshot::test_second_call_on_unchanged_tree_does_not_rebuild
  - tests/unit/test_graph_get_snapshot.py::TestGetSnapshot::test_changed_file_triggers_exactly_one_rebuild
  - tests/unit/test_graph_get_snapshot.py::TestGetSnapshot::test_load_failure_falls_back_to_build
- text: one changed file between two get_snapshot calls triggers exactly one rebuild
  evidence:
  - tests/unit/test_graph_get_snapshot.py::TestGetSnapshot::test_second_call_on_unchanged_tree_does_not_rebuild
  - tests/unit/test_graph_get_snapshot.py::TestGetSnapshot::test_changed_file_triggers_exactly_one_rebuild
  - tests/unit/test_graph_get_snapshot.py::TestGetSnapshot::test_load_failure_falls_back_to_build
- text: a never-built cache falls back to build_graph transparently via get_snapshot
  evidence:
  - tests/unit/test_graph_get_snapshot.py::TestGetSnapshot::test_second_call_on_unchanged_tree_does_not_rebuild
  - tests/unit/test_graph_get_snapshot.py::TestGetSnapshot::test_changed_file_triggers_exactly_one_rebuild
  - tests/unit/test_graph_get_snapshot.py::TestGetSnapshot::test_load_failure_falls_back_to_build
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured (static call-site audit, git grep build_graph/load_graph -- src/frob,
2026-09-19): 18 independent load_graph(cache) call sites and ~20 independent
build_graph(root, cache) call sites across src/frob/app, src/frob/gates,
src/frob/tickets/_land.py, src/frob/verify, src/frob/serve -- each reimplements
its own load-or-build-on-miss boilerplate against the SAME on-disk
.frob/cache.db, with no shared in-process or cross-process cache object.

Two concrete rebuild sources, both root-caused:

1. _docptr_kept_violations (src/frob/gates/_sys.py) builds a graph into a
   FRESH tempfile.TemporaryDirectory() cache.db on every single call -- zero
   reuse of the real repo cache, ever, by construction. This fires on every
   frob check run (full or --only sys/doc) that reaches doc004/doc006, i.e.
   an unconditional full cold rebuild every time regardless of tree staleness.

2. _load_graph_queue_lock (src/frob/gates/__init__.py), the main gate
   pipeline's graph load used by every frob check invocation, calls
   build_graph directly and never tries load_graph first -- it always pays
   the walk+staleness-check path build_graph provides, never the cheaper
   cache-hit-only path load_graph offers.

build_graph itself IS incrementally cached per-file via .frob/cache.db and
memoized per-process via memoize_per_run (T-0423), so within ONE process a
second identical call is a hit. But a ticket close-out runs 5 separate
frob check --only <stage> invocations, each a FRESH PROCESS -- memoize_per_run
provides zero reuse across those 5, so the same unchanged tree's graph is
independently walked/staleness-checked 5 times per close-out, plus the
docptr tempdir rebuild adds one guaranteed-cold rebuild PER invocation on top
of that (5 more, uncached even in principle).

T-4634 (landed today, commit deffcc7fb) already fixed one instance of this
class: land's post-publish _record_verify_intent_for_landed_commit used to
reload/rebuild a snapshot AFTER _squash_apply_on_disposable_stage had
already dirtied the tree, guaranteeing a cache miss on every land. This ticket
generalizes that fix repo-wide: one content-keyed graph cache (key = a tree
hash of the analyzable inputs, not mtimes alone) that every load_graph/
build_graph call site above goes through, so a rebuild happens only when the
key changes -- including across the 5 mandated --only processes and including
_docptr_kept_violations's throwaway build.

Plan:
- Add a content-keyed cache wrapper in src/frob/graph/__init__.py (or a new
  submodule) that every listed call site is migrated to use instead of its
  own load_graph-then-build_graph boilerplate.
- _docptr_kept_violations stops using a disposable tempdir cache; it goes
  through the same shared cache as every other caller.
- Log at INFO: "graph: reused cache key=<key>" on hit, "graph: rebuilt
  (reason=<reason>)" on miss/build, so the count above is auditable from logs
  going forward (today's land logs under /tmp/land-T-*.log have zero such
  lines -- this class of bug is currently unmeasurable from logs alone).
- docs/modules/graph.md updated with the new caching contract in the same
  change.

Acceptance:
- Test: two consecutive frob check --only <stage> runs on an unchanged tree
  build the graph zero additional times on the second run (spy/count on the
  shared cache entry point).
- Test: exactly one changed file triggers exactly one rebuild (not N, one per
  call site).
- Before/after call counts for the audited call sites, pasted in the why-file.
- No gate's findings change as a result of this change.
- _docptr_kept_violations no longer builds into a disposable tempdir cache.

Out of scope / follow-up: a general PERF00x lint rule that flags a new
load_graph/build_graph call site that does not go through the shared cache
wrapper -- file as a separate ticket if it does not fit this ticket's scope
(perf findings become lint rules, per owner directive).