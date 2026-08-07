---
id: T-0301
title: Fix 5 lithos/feldspar adoption-campaign frob bugs
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/testing/_collect.py
- src/frob/lang/_extract.py
- src/frob/gates/__init__.py
- tests/test_tickets_evidence_cli.py
- tests/test_testing.py
- tests/test_lang.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_lang.py::TestParseTsRustCppC::test_rust_directive_binds_above_multiline_rustdoc
- tests/test_lang.py::TestParseTsRustCppC::test_rust_directive_binds_regardless_of_indentation_mismatch
- tests/test_gates.py::TestTestGate::test_test005_skips_test_file_symbols
- tests/test_testing.py::TestCollectRustTests::test_collect_rust_tests_skips_lib_less_crate
- tests/test_testing.py::TestCollectRustTests::test_collect_rust_tests_still_errs_on_genuine_compile_error
- tests/test_tickets_evidence_cli.py::TestTicketEvidenceRustOracle::test_rust_node_id_from_fake_cargo_collect_cache_resolves
- tests/test_tickets_evidence_cli.py::TestTicketEvidenceRustOracle::test_no_rust_runner_declared_never_collects_rust
- tests/test_tickets_evidence_cli.py::TestTicketEvidenceRustOracle::test_rust_collection_failure_degrades_to_python_only
- frob-core/src/lib.rs::tests::wl_hash_empty_graph_is_zero
designated_repro_test: null
acceptance:
- text: Given a repo with a rust [[test.runner]] entry, when --evidence names a collected
    cargo test id, then it resolves instead of rejecting the batch
  evidence: []
- text: Given a // frob:doc placed above a multi-line /// rustdoc block, when the
    graph is built, then the directive binds to the item below
  evidence: []
- text: Given a directive at a different indentation than the item/rustdoc it binds
    to, when the graph is built, then binding still succeeds (indentation is never
    part of the binding decision)
  evidence: []
- text: Given a public test-file symbol below the branch-coverage floor, when TEST005
    runs, then it is skipped like TEST001/TEST002 already skip it
  evidence: []
- text: Given a lib-less crate (no [lib]/src/lib.rs) anywhere in the workspace, when
    rust test collection runs, then that crate is skipped with an INFO log and collection
    still succeeds for the rest of the workspace
  evidence: []
threat: null
component: null
---
## Description

Five bugs surfaced during the lithos/feldspar/graphite frob-adoption
campaign (documented in those repos' FROBLEMS.md/tickets.md escalation
notes, read read-only from this session):

A. `frob ticket evidence`/`close --evidence` validated `--evidence` ids
   against pytest collection only (`_apply_evidence` in
   `src/frob/app/ticket_runner.py`), even though `collect_rust_tests`
   already collects rust node ids into `.frob/cargo-collect.json`
   whenever a repo's `frob.toml` declares a `language = "rust"`
   `[[test.runner]]` entry -- a real rust node id could never resolve
   (feldspar T-0015 escalation).

B. A `// frob:doc` directive placed above a MULTI-line `///` rustdoc
   block failed to bind to the item below (single-line rustdoc worked).
   Root cause: `_is_trailing_comment` (src/frob/lang/_extract.py)
   compared raw tree-sitter `end_point` values; a rust `///` line-comment
   node's `end_point` bleeds into column 0 of the FOLLOWING line (a lexer
   artifact `span_of` already folds back but this helper didn't), so
   every doc-comment line whose predecessor was ALSO a doc-comment line
   was misclassified as "trailing", truncating `_block_ends`'s backward
   chain after the block's second line.

C. Investigated as a possibly separate "indentation mismatch" bug.
   Binding (`find_enclosing_symbol`/`find_following_symbol`) compares
   `RawSymbol` line spans only, never column -- indentation was never
   part of the binding decision in any of the five grammars, verified by
   constructing dedented/indented repros in python and rust both before
   and after fixing B. No separate defect was found: bug C's symptom was
   entirely explained by bug B's root cause. The honest rule (indentation
   is deliberately irrelevant to binding) is now locked by a regression
   test rather than by new indentation-aware logic.

D. TEST005's per-symbol branch-coverage floor
   (`_test005_symbols`) measured test-file symbols, unlike TEST001/
   TEST002 which already skip them via `_is_test_file` -- forcing
   env-gated test fixtures into noise waivers just to stay green.

E. Rust test collection (`_run_cargo_list`/`_cargo_list_result` in
   `src/frob/testing/_collect.py`) failed the WHOLE collection (`Err`)
   when any single crate in the workspace had no library target (e.g. a
   `cargo-fuzz` bin-only harness crate) -- `cargo test --lib -- --list`
   exits 101 for that shape exactly like it would for a genuine compile
   error, silently unvalidating every rust binding repo-wide.

## Plan

1. A: union `collect_python_tests` + `collect_rust_tests` (only when a
   rust runner is configured) in `_apply_evidence`; degrade to
   python-only with a warning on rust-collection failure so an unrelated
   cargo/pyo3 problem never blocks a purely-python ticket's evidence.
2. B: fix `_is_trailing_comment` to compare artifact-corrected end rows
   (reusing `span_of`'s existing fold rule) instead of raw `end_point`.
3. C: add regression tests locking indentation-agnostic binding; no
   separate code change (see Description).
4. D: skip `_is_test_file` symbols in `_test005_symbols`, mirroring
   TEST001/TEST002.
5. E: detect cargo's "no library targets found in package" wording in
   `_cargo_list_result` and skip that crate (INFO log, empty test list)
   instead of returning `Err`; a genuine compile error still `Err`s.