---
id: T-0408
title: 'Invariant coverage gate: harvest prose property claims into an enforced invariant
  registry (4 invariants vs 128 files asserting guarantees)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0407
tier: ticket
sprint: null
scope:
- src/frob/gates/
- invariants/
- src/frob/
- docs/modules/gates.md
- pyproject.toml
- CHANGELOG.md
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: COV001 requires a frob:doc anchor for the new inv006_gate public API; gates.md
    is the shared invariants-gate reference doc every INV rule anchors into
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: REL001 requires a version bump + changelog entry for the new public inv006_gate/INV006_SRC_DIRS/INV006_SRC_SUFFIXES
    API
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: REL001 requires a version bump + changelog entry for the new public inv006_gate/INV006_SRC_DIRS/INV006_SRC_SUFFIXES
    API
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: version bump in pyproject.toml regenerates uv.lock's own version pin
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_in_source_without_anchor_warns
- tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_with_bound_invariant_anchor_is_silent
- tests/test_gates.py::TestInv006Gate::test_waived_with_reason_is_silent
- tests/test_gates.py::TestInv006Gate::test_no_exclusivity_language_is_silent
- tests/test_gates.py::TestInv006Gate::test_outside_src_dirs_is_silent
- tests/test_gates.py::TestInv006Gate::test_missing_src_dir_is_silent
designated_repro_test: null
threat: null
component: null
---
Two-part gap the user surfaced (2026-07-20). CONTENT: only 4 formal invariants (INV-001..004) exist for a ~60k-line system, while grep finds 128 files asserting a property in prose (always/never/idempotent/thread-safe/exactly once/monotonic/guaranteed/must not). A large subset are genuine guarantees (capability-sink NoFlow, cache invalidation correctness, ledger state-machine transitions, evidence exactly-once, splice idempotence, dup alpha-rename soundness, id-allocation collision-freedom, graph-built-once) with ZERO property tests. TOOLING (the meta-gap the user named -- "frob let us get away with it for so long"): INV001/INV002 only validate DECLARED invariants (evidence + binding present); nothing checks whether ENOUGH invariants are declared, so a huge system with 4 invariants passes clean. Same class as every failure today: existence-not-completeness, early-exit-without-exhausting-the-registry.

FIX (an instance of T-0407 registry capability): the set of property claims IS a registry. (1) Harvest every prose property claim across the repo (all langs) -- always/never/idempotent/thread-safe/exactly-once/monotonic/guaranteed/must-not and the strata NoFlow/boundary claims -- as candidate invariant entries (SSOT = code prose + invariants/). (2) Each entry must be DISPOSITIONED: formalized (frob:invariant + a property/hypothesis test that actually exercises it, via the prover flow) | reworded as not-a-guarantee (removed from the claim vocabulary) | deferred (open ticket). (3) A coverage gate (INV003-style, fail-closed, ships per-project per T-0406) reds the build on any undispositioned property claim AND on proven-worthy surfaces with no invariant (a capability sink / state machine / concurrency point / idempotent op with no covering invariant). (4) frob registry audit reports invariant coverage honestly (N formalized / M deferred / K reworded / W UNACCOUNTED). Then actually FORMALIZE the real guarantees (drive the 128 down to 0 unaccounted -- dispatch the prover agent per cluster). Acceptance: adding a docstring saying "always X" with no frob:invariant reds the build; the current 128 are each dispositioned; frob passes only when invariant coverage is exhausted, not when it is merely non-empty.

META-PRINCIPLE (encode): every time we discover we "got away with" something, that is ALSO a frob enforcement gap -- file the ENFORCEMENT (the gate that would have caught it), not just the content fix.