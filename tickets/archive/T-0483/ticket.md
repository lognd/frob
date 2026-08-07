---
id: T-0483
title: 'COV: frob:tests evidence with no call-graph reachability to bound symbol,
  and frob:doc anchors on private helpers'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/graph/**
- docs/modules/gates.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_gates.py
  reason: T-draft-e6aafc2f gates work maps to tests/test_gates.py
  actor: logan
  at: '2026-07-20'
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov006_flags_test_with_no_call_graph_reachability
- tests/test_gates.py::TestCoverageGate::test_cov006_silent_when_test_calls_the_bound_symbol
- tests/test_gates.py::TestCoverageGate::test_cov006_never_fires_for_a_public_target
- tests/test_gates.py::TestCoverageGate::test_cov007_flags_doc_anchor_on_private_helper
- tests/test_gates.py::TestCoverageGate::test_cov007_silent_for_doc_anchor_on_public_symbol
designated_repro_test: null
threat: null
component: null
---
## Description

T-0297 implemented COV005 candidate (a): a directive whose (kind, target)
pair now binds a PRIVATE symbol where it bound a PUBLIC symbol in the same
file at the diff's base revision.

Candidates (b) and (c) from T-0297's original description are still open:

(b) a `frob:tests` binding whose named test function bodies do not
actually exercise the bound symbol (call-graph reachability -- ties into
the shared call-graph substrate of T-0288/T-0290).

(c) a `frob:doc #public-api` anchor on a private helper.

Filed separately per T-0297's scope discipline -- do not fold into COV005
without a fresh plan, since (b) depends on the call-graph substrate and
(c) is a different, narrower check (anchor-vs-publicness, not diff-aware
rebind).