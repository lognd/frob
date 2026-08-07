---
id: T-0867
title: shared per-function summary fixpoint engine over the resolved call graph (protocol/may-raise/capability
  clients)
state: dropped
kind: security
origin: human
created: '2026-07-23'
priority: high
parent: T-0739
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- src/frob/arch/_summaries.py
- tests/unit/test_summaries.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN a call graph with cycles WHEN the summary fixpoint runs THEN it terminates
    with sound summaries and per-function results are queryable
  evidence: []
- text: GIVEN a call through dynamic dispatch WHEN summaries are computed THEN the
    summary records Unknown fail-closed rather than assuming any resolution
  evidence: []
threat: null
component: graph
---
T-0739 child 2 (the engine). Per-function summary fixpoint engine over the call graph, shared by design with the T-0685/T-0686 may-raise analysis and the capability analysis (one engine, three clients -- no-duplication mandate). Computes per-function summaries (calls-observed, states-required/established/destroyed) to a fixpoint over the resolved call graph; dynamic dispatch is Unknown and fail-closed per T-0339 doctrine. This ticket delivers the engine + the protocol client's summary shape; the verification rules live in child 3.

## Drop reason
- 2026-07-23: duplicate of the pre-existing T-0739 child set (T-0744/T-0745/T-0746/T-0747, mostly done) -- filed 2026-07-23 without checking parent-edge children; typestate declaration surface, summary engine, verification+excuses already delivered in graph/dsl.py, graph/summary.py, gates/_protocol_summary.py