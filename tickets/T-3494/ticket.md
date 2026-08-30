---
id: T-3494
title: frob-arch WARN remainder after T-2379 (god-module/god-class/type-dispatch/self-join)
state: queued
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2379 fixed 2 unguarded-shared-write (src/frob/serve/_daemon.py, added dedicated locks -- then collapsed one into the existing module _LOCK to avoid a lexical lock-order-cycle false-positive its own fix introduced), 1 lock-order-cycle (src/frob/vet/_capability_core.py, merged two separate _span_cache_lock critical sections into one so the lexical acquisition-order scan no longer reads span-lock/docstring-lock/span-lock as a cycle -- the two locks were never actually held concurrently either before or after), and 1 type-dispatch-smell (src/frob/gates/_pii_structural/_keywords.py, isinstance chain -> exact-type dict dispatch _IDENTIFIER_NAME_EXTRACTORS). Re-measured via uv run frob check --only arch --json: 21 -> 15 frob-arch WARN findings.

NOT fixed, filed here:

self-join-deadlock (1): src/frob/serve/_socketd.py:872, _idle_monitor calling server.shutdown(). Investigated: this is very likely a detector FALSE POSITIVE -- _idle_monitor runs on a dedicated background thread (started in run_socket_daemon), while server.serve_forever() runs on the run_socket_daemon caller's own (different) thread at src/frob/serve/_socketd.py:983. shutdown() blocking until serve_forever() notices and exits is the standard, safe socketserver idle-shutdown pattern (a different thread calling shutdown() than the one running serve_forever()), not a self-join. The self-join-deadlock detector needs to distinguish "the thread calling shutdown() IS the dispatcher's own worker thread" from "a helper thread distinct from where serve_forever() runs" before this can be promoted without a permanent waiver.

type-dispatch-smell (1): src/frob/strata/_claims.py:682, _eval_one_claim's 4-arm isinstance chain dispatching NoFlow/Reach/Independent/SetEquality (falling through to _eval_bound as the default case) to different _eval_* functions with DIFFERENT signatures (_eval_bound alone takes an extra current argument) -- a real fix needs a proper Protocol/dispatch-table design for a claim-body evaluator that is part of this repo's proof-soundness critical path (strata claims), not a five-minute mechanical dict swap; needs dedicated design attention, not a rushed change to security-sensitive evaluation logic.

god-module (14) + god-class (1): src/frob/gates/_coverage.py, src/frob/gates/_waive.py, src/frob/gitio.py, src/frob/graph/__init__.py, src/frob/graph/callgraph.py, src/frob/lang/__init__.py, src/frob/lang/_common.py, src/frob/lang/_support.py, src/frob/perf/_sketch_store.py, src/frob/render/_elements.py, src/frob/stats/_sketch.py, src/frob/strata/_sysdoc.py, src/frob/tickets/__init__.py, src/frob/tickets/_evidence.py, src/frob/tickets/_models.py, src/frob/tickets/_reporting.py, src/frob/tickets/_store.py (god-module, 10-75 exports each, split-module refactors); src/frob/render/_renderer.py::RenderWriter (god-class, 16 methods vs threshold 12). Each is a genuine module/class-split design exercise (splitting a big module along its own naming/usage clusters, or extracting a mixin/helper class) -- real design judgment per T-2379's own body, not mechanical, and each is its own small campaign; do not blanket-split to hit zero.
