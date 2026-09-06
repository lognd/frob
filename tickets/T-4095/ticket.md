---
id: T-4095
title: 'H3-11: wasm-bearing dynamic import as fetch_url capability'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: low
parent: T-4089
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability_registry/_dangerous_ops_other.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a dynamic import() of a specifier resolving to a .wasm-bearing package,
    when frob vet's capability scan runs, then it is recognized as fetch_url
  evidence: []
- text: given an ordinary dynamic import with no wasm involvement, when the scan runs,
    then it is not tagged as fetch_url by this new pattern
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
H3-11 (F-296). VERIFIED: src/frob/vet/_capability_registry/_opaque.py already tracks TS dynamic import() as an OPAQUE construct (a non-literal specifier resolved at runtime, taxonomy_row="typescript:runtime:dynamic-import-call") -- but that tracking is about static-enumerability/opacity, NOT about capability tagging. Confirmed separately: no pattern anywhere in the capability registry tags a dynamic import() of a wasm-bearing package as fetch_url or any network capability. Two different concerns; the opacity tracking does not cover this gap.

FINDING THIS WOULD HAVE CAUGHT: frob sys audit reports the browser node GREEN because SYS101 only sees the via-list files it was given, and a dynamic import() of a wasm package (which triggers a network fetch to load the .wasm binary) is not recognized as a network capability at all -- so a file that genuinely performs a network-adjacent operation (loading a wasm module over the network in a browser context) sits invisible to the capability ceiling.

Proposed: add a pattern recognizing import(...) of a module specifier resolving to (or plausibly bearing) a .wasm artifact to whatever taints fetch_url today -- i.e. treat wasm-bearing dynamic imports as a network capability alongside ordinary fetch()/XHR calls already in the registry.
