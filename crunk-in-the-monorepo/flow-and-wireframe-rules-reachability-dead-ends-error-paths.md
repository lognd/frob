+++
id = "01M5XCZ119D08JHJJZ8TTR3HMR"
title = "Flow and wireframe rules: reachability, dead ends, error paths, missing decision branches, wire scenes use no brand tokens"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CXSAG0YPF18FX3KAPVX45C"
reporter = "lognd"
created = "2026-10-27T00:43:02Z"
updated = "2026-10-28T12:56:02Z"
labels = ["area:crunk", "no-story"]
scope = ["crates/crunk-rules/src/ux/flows.rs, crates/crunk-rules/tests/ux_flows.rs"]

[[acceptance]]
text = 'Given a flow with a dead-end state, when checked, then a UX finding names the state; given a decision node missing a branch, then it fires; given a scene at fidelity = "wire" using a brand token, then it fires. Edge cases: a terminal state flagged terminal=true is not a dead end; a flow with a single node is valid; unreachable states are named in stable order; a cycle with an exit is not a trap; a missing error path is reported only for steps marked fallible; fidelity absent means final and wire rules are silent'
bound = false
+++

Design crunk.md section 8 flows row. Flow file model already exists in crunk-spec flow_file.rs; this adds rules over it, no new file format.

no-story: internal engineering task in crunk-rules; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
