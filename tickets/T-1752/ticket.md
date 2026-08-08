---
id: T-1752
title: 'vet: cross-file wrapper attribution for capability detection needs frob.graph.callgraph-backed
  resolution'
state: done
kind: feature
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_vet.py
- src/frob/vet/_capability_python.py
- src/frob/vet/_capability_scan.py
- docs/modules/vet.md
- tickets/T-1752/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_vet.py
  reason: unit tests for the new cross-file wrapper attribution helpers
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/vet/**
  reason: narrow mega-glob to the two files actually touched (T-1752 is additive cross-file
    resolution, not a graph module change -- frob.graph.callgraph is only imported,
    not modified)
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/graph/**
  reason: narrow mega-glob to the two files actually touched (T-1752 is additive cross-file
    resolution, not a graph module change -- frob.graph.callgraph is only imported,
    not modified)
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/vet/_capability_python.py
  reason: narrow mega-glob to the two files actually touched (T-1752 is additive cross-file
    resolution, not a graph module change -- frob.graph.callgraph is only imported,
    not modified)
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/vet/_capability_scan.py
  reason: narrow mega-glob to the two files actually touched (T-1752 is additive cross-file
    resolution, not a graph module change -- frob.graph.callgraph is only imported,
    not modified)
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/vet.md
  reason: AFFECT001 requires updating vet.md's public-api doc for the new cross-file
    wrapper attribution; ticket.md itself is touched by ticket lifecycle commits
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1752/ticket.md
  reason: AFFECT001 requires updating vet.md's public-api doc for the new cross-file
    wrapper attribution; ticket.md itself is touched by ticket lifecycle commits
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_vet.py::TestCapabilityScan::test_wrapper_capabilities_resolve_cross_file_via_call_graph
- tests/test_vet.py::TestCapabilityScan::test_wrapper_capabilities_ignore_unrelated_cross_file_calls
designated_repro_test: null
threat: null
component: null
---
T-1626 (strata capability detection must be symbol-resolved with full alias
support) closed a python-only slice: functools.partial(dangerous, ...) and
literal-keyed dict/list dispatch tables now resolve through the existing
T-0328 import/binding-aware resolver (src/frob/vet/_capability_python.py).

Explicitly deferred from that ticket: "A helper that wraps a dangerous op
and is called from elsewhere must attribute to the caller's node" -- a
helper defined in a DIFFERENT file/module than the call site is invisible
to today's per-file capability scan regardless of alias resolution, since
the scan never looks across files.

Doing this needs frob.graph.callgraph-backed cross-file resolution over
the SCANNED DEPENDENCY's own source tree (an arbitrary third-party
package under vet, not this repo's own package graph, which is what
frob.graph.callgraph is built/tested against today). Open design
questions to resolve here:
- does a capability found N hops down a call chain attribute to every
  caller up the chain, or just the direct one?
- what traversal-depth/cycle policy is safe and fast enough for a
  dependency-scan hot path (frob vet runs per-lockfile, potentially many
  packages)?
- does this need its own call-graph build per scanned package, or can it
  reuse/adapt frob.graph.callgraph's existing machinery directly?

Read src/frob/vet/_capability_python.py (T-1626's Done report) and
src/frob/graph/callgraph.py before starting.