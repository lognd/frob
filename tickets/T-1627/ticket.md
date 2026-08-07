---
id: T-1627
title: 'strata: via must name a SYMBOL and support exactly-one-site exclusivity, not
  whitelist whole files'
state: done
kind: security
origin: human
created: '2026-08-05'
priority: high
blocked_by:
- T-1626
parent: T-1623
tier: ticket
sprint: null
scope:
- design/frob.strata
- strata-core/src/parse/grammar_node.rs
- src/frob/strata/_ast.py
- src/frob/strata/_models.py
- src/frob/strata/_infra.py
- src/frob/strata/_elaborate.py
- src/frob/strata/_effects.py
- src/frob/strata/_selfconform.py
- docs/strata/surface.md
- docs/modules/gates.md
- tests/unit/strata/test_effects.py
- tests/unit/strata/test_selfconform.py
- tests/test_lang.py
- strata-core/tests/*.rs
- strata-core/src/parse/grammar_core.rs
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'Narrowing to the exact files needed for symbol-form via + exclusive

    marker: rust grammar (may clause), surface AST/kernel MayGrant models,

    the elaborator wiring, the per-file/per-symbol capability join in

    _effects.py, self-conformance''s via-staleness join, one design file, one

    doc anchor, and targeted new/updated test files -- not the whole

    src/frob/strata/**, src/frob/vet/**, tests/**, docs/** globs.

    '
  actor: logan
  at: '2026-08-07'
- op: remove
  glob: src/frob/vet/**
  reason: 'Narrowing to the exact files needed for symbol-form via + exclusive

    marker: rust grammar (may clause), surface AST/kernel MayGrant models,

    the elaborator wiring, the per-file/per-symbol capability join in

    _effects.py, self-conformance''s via-staleness join, one design file, one

    doc anchor, and targeted new/updated test files -- not the whole

    src/frob/strata/**, src/frob/vet/**, tests/**, docs/** globs.

    '
  actor: logan
  at: '2026-08-07'
- op: remove
  glob: tests/**
  reason: 'Narrowing to the exact files needed for symbol-form via + exclusive

    marker: rust grammar (may clause), surface AST/kernel MayGrant models,

    the elaborator wiring, the per-file/per-symbol capability join in

    _effects.py, self-conformance''s via-staleness join, one design file, one

    doc anchor, and targeted new/updated test files -- not the whole

    src/frob/strata/**, src/frob/vet/**, tests/**, docs/** globs.

    '
  actor: logan
  at: '2026-08-07'
- op: remove
  glob: docs/**
  reason: 'Narrowing to the exact files needed for symbol-form via + exclusive

    marker: rust grammar (may clause), surface AST/kernel MayGrant models,

    the elaborator wiring, the per-file/per-symbol capability join in

    _effects.py, self-conformance''s via-staleness join, one design file, one

    doc anchor, and targeted new/updated test files -- not the whole

    src/frob/strata/**, src/frob/vet/**, tests/**, docs/** globs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: strata-core/src/parse/grammar_node.rs
  reason: 'Narrowing to the exact files needed for symbol-form via + exclusive

    marker: rust grammar (may clause), surface AST/kernel MayGrant models,

    the elaborator wiring, the per-file/per-symbol capability join in

    _effects.py, self-conformance''s via-staleness join, one design file, one

    doc anchor, and targeted new/updated test files -- not the whole

    src/frob/strata/**, src/frob/vet/**, tests/**, docs/** globs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/strata/_ast.py
  reason: 'Narrowing to the exact files needed for symbol-form via + exclusive

    marker: rust grammar (may clause), surface AST/kernel MayGrant models,

    the elaborator wiring, the per-file/per-symbol capability join in

    _effects.py, self-conformance''s via-staleness join, one design file, one

    doc anchor, and targeted new/updated test files -- not the whole

    src/frob/strata/**, src/frob/vet/**, tests/**, docs/** globs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/strata/_models.py
  reason: 'Narrowing to the exact files needed for symbol-form via + exclusive

    marker: rust grammar (may clause), surface AST/kernel MayGrant models,

    the elaborator wiring, the per-file/per-symbol capability join in

    _effects.py, self-conformance''s via-staleness join, one design file, one

    doc anchor, and targeted new/updated test files -- not the whole

    src/frob/strata/**, src/frob/vet/**, tests/**, docs/** globs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/strata/_infra.py
  reason: 'Narrowing to the exact files needed for symbol-form via + exclusive

    marker: rust grammar (may clause), surface AST/kernel MayGrant models,

    the elaborator wiring, the per-file/per-symbol capability join in

    _effects.py, self-conformance''s via-staleness join, one design file, one

    doc anchor, and targeted new/updated test files -- not the whole

    src/frob/strata/**, src/frob/vet/**, tests/**, docs/** globs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/strata/_elaborate.py
  reason: 'Narrowing to the exact files needed for symbol-form via + exclusive

    marker: rust grammar (may clause), surface AST/kernel MayGrant models,

    the elaborator wiring, the per-file/per-symbol capability join in

    _effects.py, self-conformance''s via-staleness join, one design file, one

    doc anchor, and targeted new/updated test files -- not the whole

    src/frob/strata/**, src/frob/vet/**, tests/**, docs/** globs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/strata/_effects.py
  reason: 'Narrowing to the exact files needed for symbol-form via + exclusive

    marker: rust grammar (may clause), surface AST/kernel MayGrant models,

    the elaborator wiring, the per-file/per-symbol capability join in

    _effects.py, self-conformance''s via-staleness join, one design file, one

    doc anchor, and targeted new/updated test files -- not the whole

    src/frob/strata/**, src/frob/vet/**, tests/**, docs/** globs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/strata/_selfconform.py
  reason: 'Narrowing to the exact files needed for symbol-form via + exclusive

    marker: rust grammar (may clause), surface AST/kernel MayGrant models,

    the elaborator wiring, the per-file/per-symbol capability join in

    _effects.py, self-conformance''s via-staleness join, one design file, one

    doc anchor, and targeted new/updated test files -- not the whole

    src/frob/strata/**, src/frob/vet/**, tests/**, docs/** globs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: 'Narrowing to the exact files needed for symbol-form via + exclusive

    marker: rust grammar (may clause), surface AST/kernel MayGrant models,

    the elaborator wiring, the per-file/per-symbol capability join in

    _effects.py, self-conformance''s via-staleness join, one design file, one

    doc anchor, and targeted new/updated test files -- not the whole

    src/frob/strata/**, src/frob/vet/**, tests/**, docs/** globs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/strata/surface.md
  reason: 'Narrowing to the exact files needed for symbol-form via + exclusive

    marker: rust grammar (may clause), surface AST/kernel MayGrant models,

    the elaborator wiring, the per-file/per-symbol capability join in

    _effects.py, self-conformance''s via-staleness join, one design file, one

    doc anchor, and targeted new/updated test files -- not the whole

    src/frob/strata/**, src/frob/vet/**, tests/**, docs/** globs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/gates.md
  reason: 'Narrowing to the exact files needed for symbol-form via + exclusive

    marker: rust grammar (may clause), surface AST/kernel MayGrant models,

    the elaborator wiring, the per-file/per-symbol capability join in

    _effects.py, self-conformance''s via-staleness join, one design file, one

    doc anchor, and targeted new/updated test files -- not the whole

    src/frob/strata/**, src/frob/vet/**, tests/**, docs/** globs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/strata/test_effects.py
  reason: 'Narrowing to the exact files needed for symbol-form via + exclusive

    marker: rust grammar (may clause), surface AST/kernel MayGrant models,

    the elaborator wiring, the per-file/per-symbol capability join in

    _effects.py, self-conformance''s via-staleness join, one design file, one

    doc anchor, and targeted new/updated test files -- not the whole

    src/frob/strata/**, src/frob/vet/**, tests/**, docs/** globs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: 'Narrowing to the exact files needed for symbol-form via + exclusive

    marker: rust grammar (may clause), surface AST/kernel MayGrant models,

    the elaborator wiring, the per-file/per-symbol capability join in

    _effects.py, self-conformance''s via-staleness join, one design file, one

    doc anchor, and targeted new/updated test files -- not the whole

    src/frob/strata/**, src/frob/vet/**, tests/**, docs/** globs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_lang.py
  reason: 'Narrowing to the exact files needed for symbol-form via + exclusive

    marker: rust grammar (may clause), surface AST/kernel MayGrant models,

    the elaborator wiring, the per-file/per-symbol capability join in

    _effects.py, self-conformance''s via-staleness join, one design file, one

    doc anchor, and targeted new/updated test files -- not the whole

    src/frob/strata/**, src/frob/vet/**, tests/**, docs/** globs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: strata-core/tests/*.rs
  reason: 'Narrowing to the exact files needed for symbol-form via + exclusive

    marker: rust grammar (may clause), surface AST/kernel MayGrant models,

    the elaborator wiring, the per-file/per-symbol capability join in

    _effects.py, self-conformance''s via-staleness join, one design file, one

    doc anchor, and targeted new/updated test files -- not the whole

    src/frob/strata/**, src/frob/vet/**, tests/**, docs/** globs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: strata-core/src/parse/grammar_core.rs
  reason: grammar_node.rs's may-clause parsing calls shared Parser helpers (at_keyword/expect_keyword/advance/etc)
    defined in grammar_core.rs; needed to satisfy scope closure for the new exclusive
    trailer
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/strata/test_effects.py::TestSymbolFormViaConformance::test_effect_inside_granted_symbol_is_clean
- tests/unit/strata/test_effects.py::TestSymbolFormViaConformance::test_effect_outside_granted_symbol_in_same_file_is_a_violation
- tests/unit/strata/test_effects.py::TestSymbolFormViaConformance::test_exclusive_grant_still_flags_a_second_site
- tests/unit/strata/test_effects.py::TestExclusiveGrammar::test_exclusive_with_symbol_form_via_parses
- tests/unit/strata/test_effects.py::TestExclusiveGrammar::test_exclusive_with_file_form_via_is_a_parse_error
- tests/unit/strata/test_effects.py::TestExclusiveGrammar::test_exclusive_with_multiple_via_entries_is_a_parse_error
- tests/unit/strata/test_effects.py::TestExclusiveGrammar::test_exclusive_with_bare_via_less_may_is_a_parse_error
- tests/unit/strata/test_effects.py::TestStaleViaSymbol::test_resolvable_symbol_is_not_flagged
- tests/unit/strata/test_effects.py::TestStaleViaSymbol::test_unresolvable_symbol_is_flagged
- tests/unit/strata/test_effects.py::TestStaleViaSymbol::test_symbol_matching_a_nested_qualname_resolves
- tests/unit/strata/test_effects.py::TestStaleViaSymbol::test_file_form_via_entries_are_never_checked
designated_repro_test: null
threat: null
component: null
---
`may "<capability>" via "<file>"` grants the capability to an ENTIRE FILE. The stated intent -- that a dangerous capability happens at exactly one controllable location -- is not what gets enforced.

Concretely today:
- `may "eval" via "src/frob/doctor.py"` permits eval anywhere in a 700+ line module.
- `may "fs.write" via [16 files]` and `may "fs.read" via [12 files]` on node `cli` alone. A sixteen-file permission list is not a chokepoint; it is an inventory.
- `may "exec" via [5 files]`, `may "env" via [6 files]`.

Two separate defects:

1. GRANULARITY. `via` should name a SYMBOL, not a file: `may "eval" via "src/frob/doctor.py::_probe_module"`. A file is an arbitrary container that grows; a function is the actual controllable location. Anything else in that file trips the gate.

2. CARDINALITY. For genuinely dangerous capabilities the correct constraint is not "in this set of places" but "in exactly ONE place". The language has no way to say that. Add it -- an exclusivity marker meaning at most one declared site, so eval, exec, and net get a real chokepoint rather than a list.

Both matter for the same reason: a permission list has no upward pressure. Every new file that writes a file gets appended to the fs.write list, and nothing ever removes one. The declaration ratchets looser as the codebase grows, which is precisely backwards for a security model.

The design pattern this should enable: funnel each capability through a single owner (all fs.write goes through one io module; every other caller calls that), then the via list is 1 and stays 1. That turns each capability into an auditable chokepoint instead of a growing inventory -- and makes the eventual waiver/capability audit tractable.

Sequencing note: symbol-level `via` requires that the capability scanner attribute a hit to an enclosing SYMBOL, not just a file. Check whether the scanner already has that (it builds tree-sitter spans for comment exclusion, so the machinery is likely present) before designing around a file-level constraint.