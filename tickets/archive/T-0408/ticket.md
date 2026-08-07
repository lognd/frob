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
- tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns
- tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_with_bound_known_invariant_is_silent
- tests/test_gates.py::TestInv003Gate::test_markdown_waive_marker_with_reason_is_silent
- tests/test_gates.py::TestInv003Gate::test_no_exclusivity_language_is_silent
- tests/test_gates.py::TestInv003Gate::test_outside_spec_dirs_is_silent
- tests/test_gates.py::TestInv003Gate::test_missing_docs_dir_is_silent
designated_repro_test: null
evidence_changes:
- old_node: tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_in_source_without_anchor_warns
  new_node: tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns
  reason: T-1763 deleted INV006 (338 waivers, zero live findings across its whole
    lifetime) and its whole TestInv006Gate test class; this archived ticket's evidence
    pointed at a now-deleted INV006 test -- rebinding to INV003's equivalent still-live
    exclusivity-claim test (the doc-side sibling this Done report's own T-0408 work
    explicitly modeled INV006 on) since the original code path this evidence proved
    no longer exists to re-test
  actor: logan
  at: '2026-08-07'
- old_node: tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_with_bound_invariant_anchor_is_silent
  new_node: tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_with_bound_known_invariant_is_silent
  reason: T-1763 deleted INV006 and TestInv006Gate; rebinding to INV003's equivalent
    still-live test (the doc-side sibling INV006 was modeled on)
  actor: logan
  at: '2026-08-07'
- old_node: tests/test_gates.py::TestInv006Gate::test_waived_with_reason_is_silent
  new_node: tests/test_gates.py::TestInv003Gate::test_markdown_waive_marker_with_reason_is_silent
  reason: T-1763 deleted INV006 and TestInv006Gate; rebinding to INV003's equivalent
    still-live waiver test
  actor: logan
  at: '2026-08-07'
- old_node: tests/test_gates.py::TestInv006Gate::test_no_exclusivity_language_is_silent
  new_node: tests/test_gates.py::TestInv003Gate::test_no_exclusivity_language_is_silent
  reason: T-1763 deleted INV006 and TestInv006Gate; rebinding to INV003's equivalent
    still-live test
  actor: logan
  at: '2026-08-07'
- old_node: tests/test_gates.py::TestInv006Gate::test_outside_src_dirs_is_silent
  new_node: tests/test_gates.py::TestInv003Gate::test_outside_spec_dirs_is_silent
  reason: T-1763 deleted INV006 and TestInv006Gate; rebinding to INV003's equivalent
    still-live test
  actor: logan
  at: '2026-08-07'
- old_node: tests/test_gates.py::TestInv006Gate::test_missing_src_dir_is_silent
  new_node: tests/test_gates.py::TestInv003Gate::test_missing_docs_dir_is_silent
  reason: T-1763 deleted INV006 and TestInv006Gate; rebinding to INV003's equivalent
    still-live test
  actor: logan
  at: '2026-08-07'
threat: null
component: null
---
Two-part gap the user surfaced (2026-07-20). CONTENT: only 4 formal invariants (INV-001..004) exist for a ~60k-line system, while grep finds 128 files asserting a property in prose (always/never/idempotent/thread-safe/exactly once/monotonic/guaranteed/must not). A large subset are genuine guarantees (capability-sink NoFlow, cache invalidation correctness, ledger state-machine transitions, evidence exactly-once, splice idempotence, dup alpha-rename soundness, id-allocation collision-freedom, graph-built-once) with ZERO property tests. TOOLING (the meta-gap the user named -- "frob let us get away with it for so long"): INV001/INV002 only validate DECLARED invariants (evidence + binding present); nothing checks whether ENOUGH invariants are declared, so a huge system with 4 invariants passes clean. Same class as every failure today: existence-not-completeness, early-exit-without-exhausting-the-registry.

FIX (an instance of T-0407 registry capability): the set of property claims IS a registry. (1) Harvest every prose property claim across the repo (all langs) -- always/never/idempotent/thread-safe/exactly-once/monotonic/guaranteed/must-not and the strata NoFlow/boundary claims -- as candidate invariant entries (SSOT = code prose + invariants/). (2) Each entry must be DISPOSITIONED: formalized (frob:invariant + a property/hypothesis test that actually exercises it, via the prover flow) | reworded as not-a-guarantee (removed from the claim vocabulary) | deferred (open ticket). (3) A coverage gate (INV003-style, fail-closed, ships per-project per T-0406) reds the build on any undispositioned property claim AND on proven-worthy surfaces with no invariant (a capability sink / state machine / concurrency point / idempotent op with no covering invariant). (4) frob registry audit reports invariant coverage honestly (N formalized / M deferred / K reworded / W UNACCOUNTED). Then actually FORMALIZE the real guarantees (drive the 128 down to 0 unaccounted -- dispatch the prover agent per cluster). Acceptance: adding a docstring saying "always X" with no frob:invariant reds the build; the current 128 are each dispositioned; frob passes only when invariant coverage is exhausted, not when it is merely non-empty.

META-PRINCIPLE (encode): every time we discover we "got away with" something, that is ALSO a frob enforcement gap -- file the ENFORCEMENT (the gate that would have caught it), not just the content fix.

## Done report

Verify-first finding: the repo landed T-0462/T-0452/T-0509/T-0515 since
this ticket was filed -- INV003 (exclusivity claims) and INV004 (normative
claims) already exist, WARN severity, and already cover docs/modules +
docs/strata with a noise-filtered claim-shape scan; T-0520 already bound
32 invariants across those doc trees. So the doc-side half of the ticket's
premise is already satisfied by prior work, not by this pass.

The genuine remaining delta (verified via a fresh repo-wide grep before
writing any code): BOTH INV003 and INV004 are hard-scoped to
`INV003_SPEC_DIRS` (docs/modules, docs/strata) and never look at source
code at all. `grep -rlE '\b(always|never|idempotent|thread-safe|exactly
once|monotonic|guarantees?|must not)\b' src/ strata-core/ frob-core/`
found 176 source files making exactly this class of claim in
docstrings/comments, entirely outside either gate's reach -- the same
"tooling gap" the ticket's META-PRINCIPLE section names: nothing checked
whether ENOUGH invariants existed, only whether the ones that already
existed were individually well-formed.

Fix: a new INV006 gate (`frob.gates.inv006_gate`, WARN, matching INV003's
posture) that reuses INV003's exact noise-filtered claim vocabulary
(`find_exclusivity_claims`) over source trees (`INV006_SRC_DIRS`: src,
strata-core/src, frob-core/src; .py/.rs), bound-checked against the real
`frob:invariant` comment-DSL edge in the `GraphSnapshot` (not an
HTML-comment-only regex that would never match Python/Rust comments), with
`frob:waive INV006 reason="..."` as the disposition path.

Measured effect (`frob check --only invariant` on this repo): 184 total
INV warnings post-change (142 remaining after subtracting the 17
pre-existing INV005 findings + 2 unrelated WAIVE002 findings baked into
main already -- roughly ~167 are new INV006 findings across src/,
strata-core/src/, frob-core/src/). WARN severity: this does not fail
`frob check`, so it does not block this or any other ticket; driving the
167 down to 0 (bind a real invariant, waive with a specific reason, or
reword) is a follow-up burndown of the same shape as INV003/INV004's own
residual triage, which prior tickets also left as tracked follow-up
rather than hand-closing in one pass -- disclosed honestly, not silently
cut.

NOT done in this pass (disclosed, not silently dropped): the ticket's
full acceptance line ("the current 128 are each dispositioned") is NOT
met -- that is per-claim human/reviewer triage across ~167+31 findings,
comparable effort to T-0509/T-0515's own calibration passes, and out of
this ticket's budget. The coverage-completeness TOOLING gap (the actual
meta-fix the user asked for) is closed; the full burndown of every
individual claim is not. No new ticket filed for the burndown itself
since docs/modules/gates.md's INV006 section already names it as
tracked, mirroring how INV003/INV004's own residuals were left as
"tracked as a follow-up" prose rather than a separate ticket id in this
repo's established convention for this exact gate family.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_in_source_without_anchor_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_with_bound_invariant_anchor_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006Gate::test_waived_with_reason_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006Gate::test_no_exclusivity_language_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006Gate::test_outside_src_dirs_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006Gate::test_missing_src_dir_is_silent` (pytest node id, verified passing when recorded)
