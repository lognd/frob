---
id: T-0287
title: 'dup: type-generalizing anti-unification (holes bind types, propose generics)'
state: done
kind: feature
origin: human
created: '2026-07-19'
priority: medium
blocked_by:
- T-0194
- T-0195
parent: null
tier: ticket
sprint: null
scope:
- frob-core/**
- src/frob/dup/**
- docs/modules/dup.md
- tickets.md
- tests/test_dup.py
- tests/unit/test_dup_template.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_dup.py
  reason: T-0287 dup work maps to tests/test_dup.py
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/test_dup_template.py
  reason: re-adding after ledger merge with main dropped this scope extension
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_dup_template.py::TestTypeHoleClassification::test_matching_type_annotations_propose_one_shared_type_var
- tests/unit/test_dup_template.py::TestTypeHoleClassification::test_value_divergence_alongside_type_divergence_stays_separate
- tests/unit/test_dup_template.py::TestTypeHoleClassification::test_type_position_in_one_member_only_stays_a_value_hole
designated_repro_test: null
acceptance:
- text: given two functions identical modulo a type (e.g. sort(list[int]) vs sort(list[str]),
    or a C++ overload set differing only in element type), when dup triage runs anti-unification,
    then the divergence is bound as a TYPE hole (not an opaque value hole) and the
    group is reported as "generalizable over type T" with the concrete instantiations
    listed
  evidence: []
- text: 'given a type-generalizable group, when the template report renders, then
    it proposes the language-correct generic abstraction: Python def f[T](...), C++
    template<typename T>, Rust fn f<T>, TS function f<T> -- one suggested signature,
    not raw $holes'
  evidence: []
- text: given a hole that binds inconsistent types across the two sides (not a single
    consistent T), then it is NOT reported as type-generalizable (no false generic
    proposal)
  evidence: []
threat: null
component: null
---
Extends the Plotkin lgg kernel (T-0194) and template report (T-0195). Today anti-unification emits value-holes at any divergence. Many real duplicate pairs differ ONLY in a type: identical algorithm over int vs str, an overload set, a monomorphized-by-hand family. The kernel must classify a hole: if both sides at a divergence are TYPE nodes (annotation, template arg, generic param, cast target) that unify to a single consistent type variable across the whole template, mark it a TYPE hole and record the per-side instantiation. The report then proposes the real fix -- a generic/templated function -- instead of a bare hole template. This is the "reverse templating / abstraction" the user asked for: dup should not just say "these are similar", it should hand back the generic signature that unifies them. Cross-language: each lang backend maps a TYPE hole to its own generics syntax. Consistency guard: a hole whose two sides need DIFFERENT type variables (no single T works) stays a value hole -- do not emit a bogus generic.