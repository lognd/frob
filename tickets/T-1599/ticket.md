---
id: T-1599
title: 'Language adapter capability matrix: make the cross-language contract statically
  enforced'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: high
blocked_by:
- T-1598
- T-2411
parent: T-1597
tier: story
sprint: post-1.0
runs_last: false
scope:
- src/frob/lang/**
- src/frob/gates/_lang_conformance.py
- src/frob/lang/_models.py
- tests/test_lang.py
- tests/test_lang_conformance_gate.py
- tests/test_lang_support.py
- docs/modules/lang.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/**
  reason: 'T-2446: real deliverables named concretely (capability matrix on the adapter
    model, a parameterized conformance suite, a conformance gate); src/frob/lang/_models.py
    is where the shared per-adapter capability declarations live, docs/modules/lang.md
    is this repo''s one existing language doc (confirmed: ls docs/modules/ shows a
    single lang.md, not per-language files), and the three named test files are the
    existing lang/conformance-gate/support suites this ticket extends -- src/frob/gates/_lang_conformance.py
    was already precisely scoped'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: tests/**
  reason: 'T-2446: real deliverables named concretely (capability matrix on the adapter
    model, a parameterized conformance suite, a conformance gate); src/frob/lang/_models.py
    is where the shared per-adapter capability declarations live, docs/modules/lang.md
    is this repo''s one existing language doc (confirmed: ls docs/modules/ shows a
    single lang.md, not per-language files), and the three named test files are the
    existing lang/conformance-gate/support suites this ticket extends -- src/frob/gates/_lang_conformance.py
    was already precisely scoped'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/lang/_models.py
  reason: 'T-2446: real deliverables named concretely (capability matrix on the adapter
    model, a parameterized conformance suite, a conformance gate); src/frob/lang/_models.py
    is where the shared per-adapter capability declarations live, docs/modules/lang.md
    is this repo''s one existing language doc (confirmed: ls docs/modules/ shows a
    single lang.md, not per-language files), and the three named test files are the
    existing lang/conformance-gate/support suites this ticket extends -- src/frob/gates/_lang_conformance.py
    was already precisely scoped'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_lang.py
  reason: 'T-2446: real deliverables named concretely (capability matrix on the adapter
    model, a parameterized conformance suite, a conformance gate); src/frob/lang/_models.py
    is where the shared per-adapter capability declarations live, docs/modules/lang.md
    is this repo''s one existing language doc (confirmed: ls docs/modules/ shows a
    single lang.md, not per-language files), and the three named test files are the
    existing lang/conformance-gate/support suites this ticket extends -- src/frob/gates/_lang_conformance.py
    was already precisely scoped'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_lang_conformance_gate.py
  reason: 'T-2446: real deliverables named concretely (capability matrix on the adapter
    model, a parameterized conformance suite, a conformance gate); src/frob/lang/_models.py
    is where the shared per-adapter capability declarations live, docs/modules/lang.md
    is this repo''s one existing language doc (confirmed: ls docs/modules/ shows a
    single lang.md, not per-language files), and the three named test files are the
    existing lang/conformance-gate/support suites this ticket extends -- src/frob/gates/_lang_conformance.py
    was already precisely scoped'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_lang_support.py
  reason: 'T-2446: real deliverables named concretely (capability matrix on the adapter
    model, a parameterized conformance suite, a conformance gate); src/frob/lang/_models.py
    is where the shared per-adapter capability declarations live, docs/modules/lang.md
    is this repo''s one existing language doc (confirmed: ls docs/modules/ shows a
    single lang.md, not per-language files), and the three named test files are the
    existing lang/conformance-gate/support suites this ticket extends -- src/frob/gates/_lang_conformance.py
    was already precisely scoped'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/lang.md
  reason: 'T-2446: real deliverables named concretely (capability matrix on the adapter
    model, a parameterized conformance suite, a conformance gate); src/frob/lang/_models.py
    is where the shared per-adapter capability declarations live, docs/modules/lang.md
    is this repo''s one existing language doc (confirmed: ls docs/modules/ shows a
    single lang.md, not per-language files), and the three named test files are the
    existing lang/conformance-gate/support suites this ticket extends -- src/frob/gates/_lang_conformance.py
    was already precisely scoped'
  actor: logan
  at: '2026-08-18'
designated_repro_test: null
acceptance:
- text: 'MEASURED 2026-08-17: significant relevant infrastructure already landed (T-0405/T-0406,
    src/frob/lang/_support.py) before this ticket''s own filing predates it (filed
    2026-08-05) -- LanguageSupport/FacetState/FacetStatus already give every registered
    language a typed per-facet IMPLEMENTED/NOT_APPLICABLE(reason)/KNOWN_GAP(tracking
    ticket) cell, derived live from each subsystem''s own registry (frob.lang/frob.vet/frob.dup/frob.arch/frob.gates._docblocks);
    LANG001 (lang_conformance_gate) already fails the build when a cell is unaccounted
    for; LANG002/LANG003 already cover the per-PROJECT half (a repo language frob
    does not parse at all, or a KNOWN_GAP present in the tree with a stale/unverifiable
    ticket ref). Deliverables 3 and 4 as originally written are LARGELY already satisfied
    by this existing mechanism -- re-verify against it before building anything parallel.'
  evidence: []
- text: 'MEASURED 2026-08-17: the existing FACETS axis (grammar/capability/dup/arch/docblock,
    src/frob/lang/_support.py FACETS tuple) is SUBSYSTEM-INTEGRATION coverage (does
    frob.vet/frob.dup/frob.arch/frob.gates._docblocks have an entry for this language),
    a DIFFERENT axis than this ticket''s own deliverable 1 (symbol walk, public/private
    determination, docstring/doc-comment extraction, comment/directive parsing incl.
    continuations, call graph edges, import/dependency edges, test discovery) -- an
    ADAPTER-CAPABILITY axis. No facet or registry for that axis exists today; this
    remains real, unbuilt work.'
  evidence: []
- text: 'MEASURED 2026-08-17: deliverable 2 (a conformance test suite parameterized
    over every registered adapter, failing when a language declares a capability it
    does not implement) does not exist -- tests/test_lang_support.py and tests/test_lang_conformance_gate.py
    test the EXISTING facet-registry-derivation and gate logic (does a registry entry
    exist), not adapter BEHAVIOR against a capability declaration. This remains real,
    unbuilt work, and is the load-bearing gap for the epic''s stated purpose (batch-adding
    20-50 languages safely).'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Make the language adapter contract explicit and statically enforced before the batch work begins.

Today a language adapter is defined by convention: some implement symbol walking, some implement doc binding, some handle directives fully and some partially, and the gaps are only discovered when a gate misbehaves on a mixed repo. Adding 20-50 languages against that is how drift becomes unmanageable.

Deliverables:

1. A written capability matrix: every capability an adapter may implement (symbol walk, public/private determination, docstring or doc-comment extraction, comment/directive parsing including continuations, call graph edges, import/dependency edges, test discovery), each marked required or optional.

2. A conformance test suite parameterized over EVERY registered adapter, so adding a language automatically inherits the full battery and cannot silently skip a capability. A language declaring a capability it does not actually implement must fail the suite.

3. A gate (or an extension of the existing lang-conformance gate) that fails when a registered adapter declares support it does not have, so the matrix cannot drift from reality.

4. An explicit, documented answer to what happens when an OPTIONAL capability is absent: which gates degrade, which skip, and how a user learns their language will not get a given check. Silent absence is the failure mode to design out -- the same class as this drive's degraded-run and truncated-suite problems, where missing analysis was indistinguishable from clean analysis.

This ticket is the machinery the epic exists to stress-test. It must land before the per-language batches.