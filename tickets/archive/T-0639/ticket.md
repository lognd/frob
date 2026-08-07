---
id: T-0639
title: 'design: detect a deprecated symbol gaining NEW callers (public-symbol caller
  graph)'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0576
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- src/frob/gates/**
- docs/modules/gates.md
- frob-deprecated-baseline.lock.json
- tests/test_gates.py
- tests/unit/gates/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: DEPR005 needs its docs/modules/gates.md anchor per docanchor/doclink gates,
    a committed baseline lock file at repo root (frob-ratchet.lock.json naming precedent),
    and gate tests
  actor: logan
  at: '2026-07-27'
- op: add
  glob: frob-deprecated-baseline.lock.json
  reason: DEPR005 needs its docs/modules/gates.md anchor per docanchor/doclink gates,
    a committed baseline lock file at repo root (frob-ratchet.lock.json naming precedent),
    and gate tests
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_gates.py
  reason: DEPR005 needs its docs/modules/gates.md anchor per docanchor/doclink gates,
    a committed baseline lock file at repo root (frob-ratchet.lock.json naming precedent),
    and gate tests
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/gates/**
  reason: DEPR005 needs its docs/modules/gates.md anchor per docanchor/doclink gates,
    a committed baseline lock file at repo root (frob-ratchet.lock.json naming precedent),
    and gate tests
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gates.py::TestDeprecatedGate::test_depr005_new_caller_errors
- tests/test_gates.py::TestDeprecatedGate::test_depr005_no_baseline_entry_is_silent
- tests/test_gates.py::TestDeprecatedGate::test_depr005_reference_set_combines_consumers_and_xref
- tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_shrinkage_drops_stale_references
- tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_never_absorbs_a_new_reference
- tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_first_seen_symbol_is_seeded_whole
- tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_symbol_no_longer_deprecated_is_dropped
designated_repro_test: null
acceptance:
- text: GIVEN a design decision recorded WHEN implemented THEN a change adding a call
    to a deprecated public symbol produces a DEPR finding naming the new call site
  evidence:
  - tests/test_gates.py::TestDeprecatedGate::test_depr005_new_caller_errors
  - tests/test_gates.py::TestDeprecatedGate::test_depr005_no_baseline_entry_is_silent
  - tests/test_gates.py::TestDeprecatedGate::test_depr005_reference_set_combines_consumers_and_xref
  - tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_shrinkage_drops_stale_references
  - tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_never_absorbs_a_new_reference
  - tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_first_seen_symbol_is_seeded_whole
  - tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_symbol_no_longer_deprecated_is_dropped
threat: null
component: null
---
T-0576's ticket body wanted a deprecated symbol gaining new callers to fire a finding, but frob.graph.callgraph's caller/reference resolution only covers PRIVATE callees by design -- a PUBLIC deprecated symbol's callers are not resolvable today. Design work: either extend the callgraph to public-symbol references (cost/precision tradeoff) or diff-based detection (a new call site referencing the symbol in a change since the directive appeared). Was T-0639 (ex-draft, id lost at land) in T-0576's worktree; drafts still do not survive land (T-0637).

Coordinator design decision 2026-07-27: baseline-ratchet, not callgraph extension. Record each DEPR003-deprecated symbol's current caller/reference set (file-level references via the exports --consumers machinery from T-0876 plus textual symbol references, same resolution the DEPR scan already trusts) into a committed .frob baseline (baseline-chunks.json precedent, T-0751). New rule DEPR004 fires at ERROR when a deprecated symbol's reference set gains a member absent from the baseline; shrinkage auto-tightens the baseline at land (PERF009 ratchet precedent). No general public-symbol callgraph work in this ticket -- that cost/precision investigation stays out of scope. This makes the ticket implementable as scoped.