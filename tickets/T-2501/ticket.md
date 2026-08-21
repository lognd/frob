---
id: T-2501
title: 'Declared provenance: one engine for confinement, config, and capability proofs'
state: queued
kind: feature
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'epic: coordination only, children carry the scopes'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Five findings from a 2026-08-18 design review converge on one mechanism,
so they are filed together rather than as independent tickets.

The unifying rule: an environmental value must have DECLARED PROVENANCE.
A path traces to a fixture or factory; a timeout, URL, limit, or
credential traces to a config object. A literal at the use site is
provenance-free and therefore unprovable. `confined to` is the filesystem
instance of this rule and the CFG* config lint is the configuration
instance -- they are not two rules that agree, they are one rule with two
value classes.

The engine already exists. `frob.graph.summary` is a per-function
bottom-up fixpoint over the call graph with an explicit lattice, an
SCC-ordered worklist, and a NO-FAIL-SILENT mandate (T-0745): an
unresolved callee POISONS the caller's summary and every transitive
caller, and unreachable functions land in `not_analyzed` rather than
being given a silently empty summary. Its docstring records the design
constraint "one engine, not two" -- a future consumer should host its own
lattice over the same worklist. Confinement provenance is that consumer.
Do NOT build a second analysis.

The poisoning semantics already implement the three-state honesty the
silent-zero doctrine (T-2391) requires: PROVEN / ESCAPED / UNKNOWN, where
UNKNOWN must never render as a pass.

Children:
1. strata fragment mechanism (imports without breakable systems)
2. ambient-vs-enumerated capability declarations (the via-list churn)
3. `confined to`, statically proven on the summary engine
4. DOC006/COV003/REF001 scoping off historical records
5. vet's resolved-identity comparison + the LEXCHECK001 trigger gap

Sequencing: (2) and (4) are pure churn removal and can land immediately.
(1) unblocks (2)'s file layout but is not required by it. (3) and (5)
share the provenance engine and should be designed together even if they
land separately. (3) must ship report-only first with a measured
PROVEN/ESCAPED/UNKNOWN census before any severity is assigned.
