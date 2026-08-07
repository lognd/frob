---
id: T-1228
title: DOC006 pointer-grammar extension -- bare identifiers, file.py::symbol, rust
  path.rs::fn, wrapped spans, private-name awareness
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: high
parent: T-1226
tier: ticket
sprint: null
scope:
- src/frob/gates/_docptr.py
- tests/test_docptr_gate.py
- design/frob.strata
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_docptr_gate.py
  reason: T-1228 pointer-grammar extension needs new coverage in the docptr test file
    per playbook constraint
  actor: logan
  at: '2026-07-29'
- op: add
  glob: design/frob.strata
  reason: T-1228 sync-interface auto-fix registers the three new TestDoc006* test
    classes in the testsuite interface, needed to clear SELFAUDIT001 SYS104
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/gates.md
  reason: 'AFFECT001: doc006_gate changed, its affects()-closure doc docs/modules/gates.md#doc006
    must move in the same diff per the pointer-grammar extension'
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_docptr_gate.py::TestDoc006FileSymbol::test_py_missing_symbol_flagged
- tests/test_docptr_gate.py::TestDoc006FileSymbol::test_py_real_symbol_passes
- tests/test_docptr_gate.py::TestDoc006FileSymbol::test_py_private_twin_noted_in_message
- tests/test_docptr_gate.py::TestDoc006FileSymbol::test_rust_missing_fn_flagged
- tests/test_docptr_gate.py::TestDoc006FileSymbol::test_rust_real_fn_passes
- tests/test_docptr_gate.py::TestDoc006FileSymbol::test_missing_file_flagged
- tests/test_docptr_gate.py::TestDoc006BareIdentifier::test_unanchored_doc_not_checked
- tests/test_docptr_gate.py::TestDoc006BareIdentifier::test_anchored_real_name_passes
- tests/test_docptr_gate.py::TestDoc006BareIdentifier::test_anchored_private_twin_noted
- tests/test_docptr_gate.py::TestDoc006BareIdentifier::test_plain_prose_word_not_flagged
- tests/test_docptr_gate.py::TestDoc006WrappedSpan::test_wrapped_backtick_span_resolves
- tests/test_docptr_gate.py::TestDoc006FileSymbol::test_ambiguous_basename_shorthand_not_flagged
- tests/test_docptr_gate.py::TestDoc006FileSymbol::test_rust_non_pub_trait_impl_fn_passes
- tests/test_docptr_gate.py::TestDoc006BareIdentifier::test_anchored_unresolved_without_twin_not_flagged
- tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_multi_anchor_doc_not_checked
- tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_spec_prose_doc_excluded
- tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_cross_file_real_symbol_passes
- tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_absent_everywhere_without_twin_not_flagged
- tests/test_docptr_gate.py::TestDoc006LedgerExclusion::test_ledger_file_symbol_placeholder_not_flagged
- tests/test_docptr_gate.py::TestDoc006LedgerExclusion::test_ledger_bare_identifier_placeholder_not_flagged
designated_repro_test: null
reviews:
- verdict: reject
  reviewer: coordinator
  findings: "REJECT: corpus check not run before close. `frob check --only docblocks`\
    \ on\nthe worktree = 1518 lines (~1479 new DOC006 findings) vs 27 on main.\nSampled\
    \ reads confirm false positives, not real doc rot:\n\n1. Kind 7 (bare identifier)\
    \ resolved only against the doc's own anchor\n   file(s), but a doc with MANY\
    \ frob:doc anchors (every module doc) is\n   effectively unscoped -- flooded ~1400\
    \ findings, including the gate's\n   own doc (docs/modules/gates.md, 147 hits)\
    \ and spec/design docs whose\n   vocabulary is DSL terms, not python identifiers,\
    \ plus real cross-file\n   symbols (AuditReport etc.) that live outside the single\
    \ anchor file\n   DOC006 happened to check.\n2. Kind 6 (file::symbol) correctly\
    \ caught real rot (moved-symbol residue,\n   private-rename cases) but also fired\
    \ on the kind's own illustrative\n   placeholder text in docs/modules/gates.md\
    \ and on ticket-ledger prose\n   syntax examples (tickets.md).\n\nRequired before\
    \ re-close: narrow kind 7 to single-anchor-module docs,\nresolve against the whole\
    \ project symbol table (not just the anchor\nfile) so cross-file real symbols\
    \ pass, exclude docs/strata/** and\ndesign/** spec-prose from kind 7, exclude\
    \ tickets.md/tickets-archive.md\nfrom both new kinds, and waive the two kinds'\
    \ own illustrative\nplaceholder mentions in docs/modules/gates.md. Re-run `frob\
    \ check --only\ndocblocks` and get the delta vs the 27-warning main baseline to\
    \ ~0 (or a\nsmall individually-waived remainder), with corpus-shaped regression\n\
    tests added."
  commit: 40e5bceb595083ada9a49600c893426aedabb2e2
  at: '2026-07-29'
threat: null
component: null
---
Resolve bare backticked identifiers within the doc's anchored module scope; support file.py::symbol and rust path.rs::fn shapes; handle line-wrapped backtick spans; flag renamed-to-private mentions. Cite src/frob/gates/_docptr.py:8-33,103,220. Ref: gate-gap class 2 in docs/audits/docs-staleness-2026-07-29.md.