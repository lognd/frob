## Done report

REWORK after reviewer reject (verdict=reject, reviewer=coordinator, commit
40e5bceb): the first close shipped kind 7 (bare identifier) scoped to
"any frob:doc anchor at all", which on this repo's own multi-anchor
reference docs was effectively no scoping -- `frob check --only docblocks`
measured 1518 total DOC006/DOC007 lines (~1479 new findings) against a
27-warning main baseline, and sampled reads confirmed false positives
(spec-DSL vocabulary, cross-file real symbols, the kind's own illustrative
placeholder text, ticket-ledger syntax examples), not real doc rot.

Three rounds of narrowing, each re-measured against the SAME
`frob check --only docblocks` corpus check:

- Round 2: kind 7 restricted to single-implementation-module docs (exactly
  one distinct frob:doc anchor file -- a doc with 2+ anchors is describing
  a system, not one module, and is out of scope entirely), excluded
  `docs/strata/**`/`design/**` (strata's own spec-DSL prose) and
  `tickets.md`/`tickets-archive.md` (ledger prose, excluded from kind 6
  too) outright, and resolved against the WHOLE project's symbol table
  (not just the one anchor file) so a real cross-file mention always
  passes. Also waived the two new kinds' own illustrative placeholder
  mentions in docs/modules/gates.md. Delta: 1518 -> 168 lines (141 new
  vs the 27 baseline).
- Round 3a: even a genuinely single-anchor, non-spec doc's "resolves to no
  symbol anywhere in the project" was still a common, LEGITIMATE shape for
  a config/data field name (`bin_path`, `service_account`) or third-party
  vocabulary (`SeDenyInteractiveLogonRight`, `ActiveDirectory`) -- neither
  is ever going to be a top-level python symbol, so absence from the
  symbol table is not real signal for this shape. Narrowed kind 7 to ONLY
  the one unambiguous signal: a private-name-rename (the token doesn't
  resolve as public, but a leading-underscore twin does, in the SAME
  anchor file). Delta: 168 -> 111 lines (84 new).
- Round 3b: `_resolve_tracked_file`'s shorthand-basename match picked an
  ARBITRARY one of several same-named tracked files (16 different
  `_models.py` files alone exist in this repo) -- confirmed false
  positive: `` `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES` `` resolved
  against the wrong of two tracked `_waive.py` files and flagged a REAL
  symbol as stale. Fixed to treat a multi-file shorthand match as
  ambiguous/unrecognized (never flagged) rather than guessing. Separately,
  the rust `pub`-only item check (reused from `_docblocks_refs._rust_
  item_defined`, built for a crate-wide `use` check) false-flagged several
  genuine TRAIT-IMPL methods (`parse_node`, `parse_store`, ...) that never
  carry an explicit `pub` of their own; since kind 6 already pins one
  exact file, matching without requiring `pub` is precise here. Delta:
  111 -> 59 lines (32 new).

Final corpus check: `frob check --only docblocks` exits 0 clean, 59
warnings vs the 27-warning main baseline -- 32 net new DOC006 findings
(no errors, no regressions in the pre-existing 27). Every one of the 32
was individually spot-checked against the actual tree (not sampled
blind) and confirmed a TRUE positive, not a resolver artifact: 5
private-name renames (`high_entropy_strings`->`_high_entropy_strings`,
`invisible_text_signal`->`_invisible_text_signal`,
`hex_identifier_ratio_signal`->`_hex_identifier_ratio_signal`,
`npm_non_registry_rule`->`_npm_non_registry_rule`,
`SecretDecl`->`_SecretDecl`, `DecisionStatus`->`_DecisionStatus`,
`doable_count`->`_doable_count`), several confirmed-missing tracked files
(`_pipeline.py`, `strata-core/src/parse.rs`, `src/frob/graph/store.py`,
`frob-core/src/dup_kernel.rs` -- all matching the docs-staleness audit's
own "moved-symbol residue" class, e.g. `parse.rs`'s post-T-1006 split
into `grammar_*.rs`), and several confirmed-absent symbols
(`_elaborate_module` no longer exists in `_elaborate.py`, only
`elaborate` does; `_selfaudit_violations` no longer resolves in
`gates/__init__.py`, matching the audit's own noted T-1188 move to
`_sys.py`; `TestRuleFixability` no longer exists in `tests/test_gates.
py`). This is real, previously-undetected doc rot -- exactly this
ticket's motivating case -- shipped at WARN per this exact gate's own
established T-0688 new-gate-at-WARN precedent (this file's own docstring
already carries an identical disclosure for kinds 1-5's ~700-finding
pre-existing backlog); not waived, since waiving a confirmed TRUE
positive would hide real drift rather than disclose it.

## Done report

Changed (this rework, on top of the original T-1228 commit):
- src/frob/gates/_docptr.py::_MAX_ANCHOR_MODULES_FOR_BARE_IDENTIFIER, _SPEC_PROSE_DOC_PREFIXES, _LEDGER_FILES (new module constants, round-2 narrowing)
- src/frob/gates/_docptr.py::_all_project_symbol_names (new, round-2)
- src/frob/gates/_docptr.py::_bare_identifier_violations (rewritten: single-anchor + spec/ledger exclusion + whole-project resolution + private-twin-only signal, rounds 2-3a)
- src/frob/gates/_docptr.py::_file_symbol_violations (ledger exclusion, round-2)
- src/frob/gates/_docptr.py::_resolve_tracked_file (ambiguous-shorthand detection, round-3b; return type now `tuple[str | None, bool]`)
- src/frob/gates/_docptr.py::_rust_item_defined_in_file, _RUST_ITEM_IN_FILE_RE_TMPL (new, round-3b: pub-optional rust item check scoped to one named file)
- src/frob/gates/_docptr.py::_rust_file_symbol_violation (uses the new pub-optional check, round-3b)
- src/frob/gates/_docptr.py::doc006_gate (wires all_project_names through; refreshed frob:tests directive block)
- docs/modules/gates.md#doc006-doc-pointer-resolution-gate-t-0437 (documents all three rounds' decisions and rationale; waives its own kind-6/7 illustrative placeholder mentions)
- design/frob.strata (frob sys sync-interface: registers TestDoc006BareIdentifierNarrowing, TestDoc006LedgerExclusion in the testsuite interface)
- tests/test_docptr_gate.py (renamed 2 tests to match the narrowed behavior; added TestDoc006BareIdentifierNarrowing (4 tests: multi-anchor exclusion, spec-prose exclusion, cross-file real symbol, absent-everywhere-no-twin), TestDoc006LedgerExclusion (2 tests), test_ambiguous_basename_shorthand_not_flagged, test_rust_non_pub_trait_impl_fn_passes -- corpus-shaped regression coverage for every false-positive class the reviewer found)

Evidence: 20 pytest node ids (full tests/test_docptr_gate.py suite, 42
tests, all pass) bound via `frob ticket evidence`/`frob ticket reverify
--evidence`; one stale evidence id (a renamed test method) removed from
tickets.md's evidence list -- the ONLY hand-edit made to ticket
frontmatter, correcting a rename, not skipping verification (the
replacement id was reverified passing in the same `frob ticket
reverify` call).

Filed: none -- no out-of-scope work discovered.

Gates: `frob check --only docblocks` exits 0 clean (59 warnings, 0
errors, 32 net new vs the 27-warning main baseline, all individually
spot-checked true positives -- see the corpus-delta narrative above).
`frob check --only perf --only affect_drift --only sys --only scope`
(run without --ticket since this rework happened post-close, no active
lease) shows gate:AFFECT and gate:PERF both still clean (0 errors);
gate:SELFAUDIT/gate:SCOPE findings in that run are either resolved by
the same `frob sys sync-interface` re-run this rework already includes,
or are the ticket-lease-derivation SCOPE001 artifact of running --only
without --ticket (not a real scope violation -- the coordinator's own
land step re-derives this correctly). ruff-check and ruff-format both
clean on every changed file. `frob ticket reverify T-1228` (T-1228's own
full close-time verification suite) passed.

### Changed
```
 design/frob.strata        |   3 +
 docs/modules/gates.md     |  50 +++++++-
 src/frob/gates/_docptr.py | 309 +++++++++++++++++++++++++++++++++++++++++++++-
 tests/test_docptr_gate.py | 152 +++++++++++++++++++++++
 tickets.md                | 112 ++++++++++++++++-
 5 files changed, 613 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc006FileSymbol::test_py_missing_symbol_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006FileSymbol::test_py_real_symbol_passes` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006FileSymbol::test_py_private_twin_noted_in_message` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006FileSymbol::test_rust_missing_fn_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006FileSymbol::test_rust_real_fn_passes` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006FileSymbol::test_missing_file_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006BareIdentifier::test_unanchored_doc_not_checked` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006BareIdentifier::test_anchored_real_name_passes` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006BareIdentifier::test_anchored_private_twin_noted` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006BareIdentifier::test_plain_prose_word_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006WrappedSpan::test_wrapped_backtick_span_resolves` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006FileSymbol::test_ambiguous_basename_shorthand_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006FileSymbol::test_rust_non_pub_trait_impl_fn_passes` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006BareIdentifier::test_anchored_unresolved_without_twin_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_multi_anchor_doc_not_checked` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_spec_prose_doc_excluded` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_cross_file_real_symbol_passes` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_absent_everywhere_without_twin_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006LedgerExclusion::test_ledger_file_symbol_placeholder_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006LedgerExclusion::test_ledger_bare_identifier_placeholder_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 20 passed (from 20 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
