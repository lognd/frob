---
id: T-0341
title: 'EPIC: strata conformance totality -- every module binds to a node, declares
  its exact interface + purpose, effects proven against code'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: epic
sprint: null
scope:
- src/frob/strata/**
- src/frob/vet/**
- src/frob/graph/**
- tickets.md
- docs/modules/strata.md
- tests/unit/strata/
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/strata.md
  reason: T-0341 strata work maps to docs/modules/strata.md
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/strata/
  reason: T-0341 strata work maps to tests/unit/strata/
  actor: logan
  at: '2026-07-20'
evidence:
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_undeclared_public_symbol_fires
- tests/unit/strata/test_selfconform.py::TestPurposeContract::test_read_only_purpose_with_write_effect_fires
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires
- tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_expired_waiver_refires_and_is_flagged
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_arch_checks_gate_reports_zero_unaccounted_slh_entries
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestConformanceChecksBoundToDenominator::test_each_conformance_row_handled_by_its_real_check
designated_repro_test: null
acceptance:
- text: 'COVERAGE TOTALITY (SYS-COV): every deployable/public module -- and every
    module the binding-aware scanner finds ANY capability in -- must bind to exactly
    one strata node; unbound-but-capable code is a hard failure (the model cannot
    omit dangerous code)'
  evidence:
  - tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103
- text: 'INTERFACE CONFORMANCE (exact): a node''s declared interface must EQUAL the
    code''s actual public surface -- an undeclared public export fails, and a declared-but-absent
    symbol fails; every module is forced to declare its interface and keep it in lockstep
    with the code'
  evidence:
  - tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_undeclared_public_symbol_fires
- text: 'PURPOSE CONTRACT: every node declares a PURPOSE carrying an allowed-effect
    profile; an effect outside the purpose''s profile (e.g. a network effect in a
    declared logging/pure purpose) fires and needs a reasoned discharge -- purpose
    is a typed constraint, not a comment'
  evidence:
  - tests/unit/strata/test_selfconform.py::TestPurposeContract::test_read_only_purpose_with_write_effect_fires
- text: 'BINDING TOTALITY + EFFECT CONFORMANCE: code<->node binding is a TOTAL function
    over capable code (no laundering logic into an unbound file); the exhaustive binding-aware
    scanner''s extracted effect set must be a subset of what the node declares, declared
    >= actual, with opaque/unresolvable effects failing closed (T-0339)'
  evidence:
  - tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires
- text: 'BOUNDED ESCAPE HATCHES + GATED CONFIG: waivers/assumes are counted, reason-required,
    staleness-dated, and budget-limited (waive-everything is itself a smell); baseline-view
    and threshold loosening is an audited event, never silent'
  evidence:
  - tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_expired_waiver_refires_and_is_flagged
threat: elevation-of-privilege
component: null
---
The user asked (2026-07-20): 'what mechanisms enforce conformance to the .strata file? Do we force every module to declare its purpose and interface?' -- and to harden it adversarially. Design north-star: docs/design/structural-linter-adversarial-hardening.md. Today _code_binding.py (bind_code/ConformanceReport/check_import_conformance) and _effects.py::check_capability_conformance exist, and T-0331 already mandates 'NO obligation satisfied by bare declaration' -- but conformance is NOT TOTAL, which is the evasion surface: (1) un-modeled modules escape all obligations; (2) a node can declare a partial interface while the code exports more; (3) nothing binds a module's PURPOSE to an allowed-effect profile; (4) binding need not be total, so logic can be laundered into an unbound file. This epic closes those into the five acceptance criteria above (SYS-COV coverage totality, exact interface conformance, purpose contract, binding totality + effect conformance, bounded escape hatches + gated config), each a child ticket. Soundness rests entirely on the exhaustive binding-aware scanner (T-0328/T-0337/T-0339) -- this epic is the conformance layer ON TOP of that foundation. Coincident with the arch epic (T-0330) and strata-systems epic (T-0331); this is the 'the model cannot lie about the code' guarantee made total.

EXHAUSTIVENESS DRIFT-LOCK (T-0343, 2026-07-20 mandate 'implementation MUST address EVERYTHING the exhaustive researcher found'): this epic's implementation binds to the corpus DENOMINATOR MANIFEST via T-0343's N:M coverage meta-test. Denominator source: the conformance mechanisms in structural-linter-adversarial-hardening.md (coverage/interface/purpose/binding/effect totality). Every relevant manifest entry must map to >=1 registered check/obligation/recommender-rule OR carry an explicit reasoned deferral (advisory/not-checkable/ticketed); (addressed union deferred) == TOTAL. The epic CANNOT close while any researched entry is un-addressed and un-deferred -- the corpora (docs/design/*) are the enforceable denominator, not just reading.