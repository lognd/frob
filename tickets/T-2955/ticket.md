---
id: T-2955
title: 'frob-dup: triage tests/ duplicate cluster (~490 groups)'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: T-2378
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-2955/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tickets/T-2955/**
  reason: documenting the detector-narrowing triage decision; no production code change
    in this ticket
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
acceptance:
- text: given the tests/ frob-dup cluster measured in this ticket's body, when triaged,
    then a decision (extract / per-group waive / detector-narrowing proposal) is recorded
    for every sub-cluster, decomposed into further children as needed
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed as a T-2378 sibling per the "decompose, do not mega-land" instruction.

Cluster (frob-dup, unscoped, measured 2026-08-26): the test-suite is by far
the largest share of both exact and renamed findings -- roughly 490 of the
557 unaccounted groups have EVERY fragment inside tests/. Rough per-file
breakdown (dominant files): tests/unit/strata (76), tests/test_gates.py
(50), tests/test_vet.py (23), tests/unit/test_arch.py (16),
tests/test_docptr_gate.py (15), tests/unit/perf (10),
tests/test_pii_structural_gate.py (10), tests/test_graph.py (10),
tests/unit/graph (9), tests/test_dup.py (7), plus a long tail of 3-6-count
groups across dozens of other test files (see the tool's frob-dup output
for the full list).

Per the parent ticket's own instruction #2: "Test fixtures that
deliberately repeat a shape for readability are not debt." A first pass at
several of these (arrange-block boilerplate: tmp_path setup, a small
parametrized helper, a shared assertion shape) strongly suggests most of
this cluster is exactly that -- deliberate repetition for per-test
readability, not desync risk, since each test's fixture is read and
maintained in isolation.

This ticket is NOT pre-decided extract vs waive vs narrow-detector. Given
the volume, the likely right shape is: (a) spot-check a sample of the
larger groups (tests/unit/strata's 76, tests/test_gates.py's 50) for any
GENUINE shared-logic case masquerading as "just a test", extract those; (b)
for the rest, propose either a `frob:waive DUP001/DUP002` per group with a
real per-group reason (slow, hundreds of groups), OR a detector-level
change (narrow frob-dup to exclude tests/ entirely, or raise its
size/severity threshold for files under tests/) -- the latter needs a
deliberate decision from whoever owns frob-dup's design, so raise it
explicitly rather than waiving hundreds individually. Decompose further by
directory before dispatching.

Re-measure via: uv run frob check --json --only static, filter
tool=="frob-dup", filter messages where every location starts with "tests/".
