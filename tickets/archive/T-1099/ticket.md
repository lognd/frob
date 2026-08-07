---
id: T-1099
title: 'strata-core: split parse.rs (4346 lines) into grammar-family modules'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- strata-core/src/
- docs/guides/extending/strata-surface-grammar.md
- tickets-archive.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/unit/strata/
  reason: 'narrow scope: T-1099 is a pure Rust module split, does not need broad python
    test tree access which another agent needs this wave'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/guides/extending/strata-surface-grammar.md
  reason: T-1099's Rust module split moved Parser.parse_program to grammar_policy.rs;
    the doc's frob:describes edge must follow or DRIFT002 fires (scope-closure warning
    at scope-narrow time flagged this exact file)
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tickets-archive.md
  reason: T-1099's parse.rs->parse/mod.rs rename breaks archived tickets' frozen frob:tests
    evidence citations (COV003); mechanical path-only substitution, same qualname
    (parse::tests::X), no narrative content touched
  actor: logan
  at: '2026-07-28'
evidence:
- strata-core/src/parse/mod.rs::tests::parses_bare_module
- strata-core/src/parse/mod.rs::tests::round_trip_small_design
- strata-core/src/parse/mod.rs::tests::parses_policy_forbid_call_and_import
- strata-core/src/parse/mod.rs::tests::parses_refine_happy_path
- strata-core/src/parse/mod.rs::tests::fuzz_safe_random_bytes_never_panic
designated_repro_test: null
acceptance:
- text: given the strata-core crate, when the split lands, then parse.rs holds only
    the parser spine, grammar families live in their own modules, no file exceeds
    2000 lines, and cargo test plus the full strata litmus suite pass unchanged
  evidence:
  - strata-core/src/parse/mod.rs::tests::parses_bare_module
  - strata-core/src/parse/mod.rs::tests::round_trip_small_design
  - strata-core/src/parse/mod.rs::tests::parses_policy_forbid_call_and_import
  - strata-core/src/parse/mod.rs::tests::parses_refine_happy_path
  - strata-core/src/parse/mod.rs::tests::fuzz_safe_random_bytes_never_panic
threat: null
component: null
---
parse.rs accreted the whole strata grammar across T-0629/T-0700/T-0702 and siblings (4346 lines). Split by grammar family per the T-1072/T-1086 discipline translated to Rust module conventions (mod files, pub(crate) surfaces re-exported from parse.rs or lib.rs so the python bindings and goldens stay byte-identical). Discovered alongside the large-file gate gap (T-1102); the split makes the Rust tree pass the ceiling that gate will enforce.