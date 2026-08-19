---
id: T-2365
title: Adapter-capability axis + behavioral conformance suite for the 6 registered
  languages
state: done
kind: feature
origin: human
created: '2026-08-17'
priority: medium
parent: T-1599
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/_support.py
- src/frob/gates/_lang_conformance.py
- docs/modules/lang.md
- tests/test_lang_support.py
- tests/test_lang_conformance_gate.py
- tickets/T-2408/**
- tickets/T-2409/**
- tickets/T-2410/**
- tickets/T-2411/**
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tickets/T-2408/**
  reason: own filed draft follow-up ticket.md files land in this ticket's own commit
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tickets/T-2409/**
  reason: own filed draft follow-up ticket.md files land in this ticket's own commit
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tickets/T-2410/**
  reason: own filed draft follow-up ticket.md files land in this ticket's own commit
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tickets/T-2411/**
  reason: own filed draft follow-up ticket.md files land in this ticket's own commit
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_waive.py
  reason: closing the ticket requires registering the new LANG004 gate rule id in
    _KNOWN_GATE_RULES (T-1937 land-time construct gate) -- a mandatory one-line registration,
    not new functionality
  actor: logan
  at: '2026-08-18'
body_changes:
- mode: append
  reason: 'COV003 disposition: recording obsolete-superseded per T-2408''s own closure,
    not a rebind -- coordinator-approved (T-2669 triage)'
  actor: logan
  at: '2026-08-19'
  old_length: 3644
  new_length: 4811
evidence:
- tests/test_lang_support.py::TestDeriveCapabilityRegistry::test_covers_every_supported_language
- tests/test_lang_support.py::TestDeriveCapabilityRegistry::test_every_language_declares_every_capability
- tests/test_lang_support.py::TestDeriveCapabilityRegistry::test_real_registry_has_no_conformance_violations
- tests/test_lang_support.py::TestDeriveCapabilityRegistry::test_strata_call_graph_is_not_applicable
- tests/test_lang_support.py::TestDeriveCapabilityRegistry::test_typescript_import_graph_is_a_reasoned_known_gap
- tests/test_lang_support.py::TestCapabilityConformanceViolations::test_missing_capability_fails
- tests/test_lang_support.py::TestCapabilityConformanceViolations::test_fully_registered_language_passes
- tests/test_lang_support.py::TestCapabilityConformanceViolations::test_unreasoned_known_gap_fails
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_every_registered_language_is_covered
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_directive_continuation_folds_correctly_not_just_present
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_broken_continuation_fixture_is_caught_not_rubber_stamped
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_no_symbols_fixture_is_caught_not_rubber_stamped
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_unchecked_capability_is_named_not_silently_true
- tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate::test_real_registry_is_behaviorally_clean
- tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate::test_wrong_implemented_claim_fails
designated_repro_test: null
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: d7a147d18c6c129c67987e3b4add9845cd198063
---
Split from T-1599 after a 2026-08-17 re-measurement (recorded on the
parent's own acceptance list via `frob ticket accept`, not hand-edited).

T-1599 predates T-0405/T-0406 (both landed after T-1599 was filed
2026-08-05): those tickets already built `src/frob/lang/_support.py`'s
`LanguageSupport`/`FacetState`/`FacetStatus` contract plus LANG001-003
(src/frob/gates/_lang_conformance.py) enforcing it -- a real,
already-shipped answer to T-1599's deliverables 3 (a gate that fails
when a registered adapter's declared support does not match reality)
and 4 (documented, non-silent degrade states: NOT_APPLICABLE with a
reason, KNOWN_GAP naming a tracking ticket that LANG003 verifies still
resolves).

DELIBERATELY NOT BLOCKED on T-1598 (the 20-50 language target-list
research ticket, still queued): this ticket's scope is the capability
axis for the SIX adapters already registered today (python/c/kotlin/
rust/strata/typescript, `frob.lang.supported_languages`) -- it needs no
information from T-1598's ranking work to be buildable and testable now.

WHAT IS ACTUALLY MISSING (the corrected, narrowed scope):

1. A SECOND facet-shaped axis, distinct from `_support.py`'s existing
   FACETS tuple (which is subsystem-INTEGRATION coverage: does
   frob.vet/frob.dup/frob.arch/frob.gates._docblocks have an entry).
   This new axis is ADAPTER-CAPABILITY coverage: does the adapter itself
   implement symbol walking, public/private determination, docstring or
   doc-comment extraction, comment/directive parsing (including
   continuations -- frob's own `frob:tests \` multi-line directive
   syntax is the sharpest test case), call graph edges, import/
   dependency edges, test discovery. Each capability marked required or
   optional, same IMPLEMENTED/NOT_APPLICABLE(reason)/KNOWN_GAP(ticket)
   shape `_support.py` already established -- reuse that shape and its
   pydantic model conventions, do not invent a second one.

2. A BEHAVIORAL conformance test suite, parameterized over every
   registered adapter (`frob.lang.supported_languages`), that actually
   EXERCISES each declared capability against a real fixture per
   language and fails if a declared-IMPLEMENTED capability does not
   actually work -- distinct from the existing `test_lang_support.py`/
   `test_lang_conformance_gate.py`, which test the REGISTRY declarations
   (is there an entry) not adapter BEHAVIOR (does the entry's claim
   hold). This is the load-bearing gap: a wrong registry entry today
   would pass every existing test.

3. Extend LANG001 (or add a narrowly-scoped LANG004, whichever avoids
   duplicating `derive_language_registry`'s existing shape -- check
   before adding a new rule id, per the repo's no-duplication rule) to
   also fail when a language declares an adapter-capability it does not
   actually implement, using this ticket's new suite as the oracle.

Standing repo constraints apply unchanged (symbolic not lexical, typani
Result/ErrorSet, frozen pydantic models, log everything, docs
same-change, no waivers).

Acceptance:
- The adapter-capability axis is declared for all 6 currently-registered
  languages, each capability marked required/optional with a real
  IMPLEMENTED/NOT_APPLICABLE/KNOWN_GAP status.
- The behavioral conformance suite runs against every registered adapter
  and demonstrably fails on a deliberately-wrong declaration (a
  must-fail positive control, not just a must-pass suite).
- The gate extension fails on the same deliberately-wrong declaration
  used above, and passes clean on the current, honest tree.
- docs/modules/lang.md documents the new axis alongside the existing
  facet-contract section.

COV003 OBSOLETE-SUPERSEDED (T-2669 triage, 2026-08-19): this ticket's
evidence citation
`tests/test_lang_support.py::TestDeriveCapabilityRegistry::test_typescript_import_graph_is_a_reasoned_known_gap`
no longer resolves. Investigated: this is NOT a rename. The test that
replaced it, `test_typescript_import_graph_is_implemented`, asserts
the OPPOSITE of the original claim.

This ticket's own KNOWN_GAP_TRACKING_TICKETS declared T-2408 as the
tracker for TypeScript's import_graph capability gap. T-2408 (done)
built the missing `_imports_typescript`/`_imports_rust`/
`_imports_kotlin` walkers -- the gap this ticket disclosed is closed.

Disposition: the ORIGINAL INVARIANT this test proved ("TypeScript
import_graph is a reasoned, disclosed gap") was REPLACED by T-2408's
own work, not merely re-proven under a new name elsewhere. Do NOT
rebind this citation -- the successor test proves the opposite of what
this ticket originally claimed, and binding to it would misrepresent
this ticket as still proving a gap that no longer exists. This COV003
finding is accepted, permanent, disclosed residue: the capability
this ticket declared missing has since shipped.