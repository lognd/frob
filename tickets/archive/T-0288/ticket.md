---
id: T-0288
title: 'dup: helper-inlining / call-graph-aware triage (see through arch-forced splits)'
state: done
kind: feature
origin: human
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/**
- src/frob/graph/callgraph.py
- tests/**
- docs/modules/dup.md
- docs/modules/graph.md
- tickets.md
- CHANGELOG.md
- pyproject.toml
- uv.lock
- .frob-release.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_dup_inline.py::TestHelperInliningLitmus::test_split_helpers_detected_with_inlining
- tests/test_dup_inline.py::TestSharedHelperNotDuplication::test_shared_helper_not_flagged_at_threshold_0_7
designated_repro_test: null
acceptance:
- text: given two functions whose shared logic was each extracted into differently-named
    PRIVATE helpers (per frob arch small-helper pressure), when dup triage compares
    them, then it resolves the private/module-local helper calls and compares over
    the inlined (or call-graph-closure) body, and still reports the pair as duplicate
  evidence: []
- text: given a private helper called from exactly one site, when triage inlines for
    comparison, then the inlining is bounded (depth + total-node ceiling) and NEVER
    follows public API calls or recurses infinitely (recursion/cycle guard)
  evidence: []
- text: given a cluster of near-identical tiny helpers created by over-splitting,
    when dup runs, then those helpers themselves are reported as a dup group (the
    inverse failure mode -- arch-forced fragmentation producing duplicate helpers)
  evidence: []
threat: null
component: null
---
Directly motivated by the arch<->dup tension the user raised: frob arch enforces many small private helpers, which (a) HIDES Type-3/4 duplication -- two functions with the same logic split into differently-named helpers now hash/compare as different call skeletons -- and (b) CREATES duplication -- over-splitting spawns families of near-identical one-line helpers. dup currently compares whole bodies (_r1_hash/_r2_hash and the region/anti-unify passes all operate on a single symbol body), so it is blind to logic that lives one call-hop away. Fix: before structural comparison, resolve calls to PRIVATE (leading-underscore / module-local, not re-exported) helpers and splice their bodies into the comparison unit -- a bounded call-graph closure, depth-limited, cycle-guarded, public-API-stopping, node-count-capped (fall back to un-inlined body past the cap). This makes dup measure the ACTUAL logic, not the arch-imposed decomposition. Pair (b): also run a dup pass over the helper population itself so over-splitting is caught. Keep inlining a triage-only view (do not rewrite source); report spans point at the real helper definitions.