---
id: T-2706
title: LANG004 reports frob's own src/frob/ paths into consumer repos, where they
  are unactionable
state: in-progress
kind: bug
origin: human
created: '2026-08-20'
priority: high
blocked_by:
- T-2682
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_lang_conformance.py
- src/frob/gates/__init__.py
- src/frob/repo_meta.py
- tests/test_lang_conformance_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_lang_conformance.py
  reason: gate self-conformance path + repo_root wiring per T-2706 plan
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/gates/__init__.py
  reason: gate self-conformance path + repo_root wiring per T-2706 plan
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/repo_meta.py
  reason: gate self-conformance path + repo_root wiring per T-2706 plan
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_lang_conformance_gate.py
  reason: behavioral tests for capability_conformance_gate repo-scoping
  actor: logan
  at: '2026-08-20'
evidence:
- tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate::test_real_registry_is_behaviorally_clean
- tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate::test_wrong_implemented_claim_fails
- tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate::test_consumer_repo_is_silent_even_with_a_broken_claim
- tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate::test_repo_root_with_no_pyproject_is_silent
- tests/test_lang_conformance_gate.py::TestCapabilityConformanceWiring::test_capability_conformance_fires_through_real_gate_dispatch
designated_repro_test: tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate::test_consumer_repo_is_silent_even_with_a_broken_claim
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by a downstream consumer repo (aprog-public) on frob 0.530.0,
2026-08-20.

## Symptom

Running `frob check` in a CONSUMER repo emits four errors anchored at a
path inside frob's OWN source tree:

    src/frob/lang/_support.py:0  LANG004: strata capability
    'directive_parse' is declared IMPLEMENTED but failed its behavioral
    check: no behavioral fixture registered for language 'strata'

(same for `doc_extract`, `publicness`, `symbol_walk`)

`src/frob/` does not exist in the consumer repo. The consumer is handed
errors about frob's internal language-support table, anchored at a file
path that does not resolve locally, and nothing in that repo can register
a strata behavioral fixture. Unactionable downstream.

## This is the known portability class

This is PORT001's territory: gate code that hardcodes `src/frob/` paths
either silently passes or falsely fires when run off-repo. The rule is
declare, never hardcode. Check whether LANG004's fixture-registry check
is one of the already-catalogued hardcoded-path sites before writing a
new mechanism.

## Fix direction, and the choice to make explicitly

Either:
(a) suppress the self-conformance half of LANG004 outside frob's own
    tree -- it is an assertion about FROB's adapters, not the consumer's; or
(b) anchor it somewhere meaningful to the consumer.

Prefer (a), but state the decision in the ticket rather than leaving it
implicit. IMPORTANT: whichever is chosen, frob's own repo must STILL fire
these findings -- they are real there. A fix that silences the rule
everywhere is a regression, not a fix.

## Positive controls, both directions

- `frob check` in a consumer repo emits NO finding anchored at a path
  that does not exist in that repo
- `frob check` in frob's OWN repo still reports the four strata-capability
  findings (they are genuine self-conformance debt)
- the 'strata' language case specifically: a consumer with no strata
  fixtures is silent; frob with a missing fixture still fires