---
id: T-2502
title: 'strata fragments: imports that cannot break a system apart'
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: T-2501
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- strata-core/src/parse/
- src/frob/strata/_parse.py
- src/frob/strata/_ast.py
- src/frob/strata/_multifile.py
- src/frob/strata/_design_load.py
- docs/strata/surface.md
- tests/unit/strata/test_fragments.py
- editors/vscode-strata/syntaxes/strata.tmLanguage.json
- docs/guides/extending/strata-surface-grammar.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/
  reason: 'over-broad: 1915 closure warnings would lease most of the strata package;
    the grammar+loader change lives in the parser and the two parse-layer modules'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/strata/_parse.py
  reason: the .strata loader entrypoint the fragment/glob logic changes
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/strata/_ast.py
  reason: fragment node types (part-of / extend) enter the AST here
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/strata/_multifile.py
  reason: the extend-only fragment mechanism (module frob { } root closure, part-of
    fragment header, extend node { } merge) is a cross-file concept by definition
    -- one-root enforcement, unknown-root/unknown-node refusal, and the append-only
    never-weaken merge of extend grants against the root's already-elaborated grants
    structurally live in the existing T-1196 cross-file join (_multifile.py::elaborate_merged)
    and its loader caller (_design_load.py), not in the single-file grammar/AST layer
    alone; grammar+AST (declared scope) enforce the syntactic half (extend blocks
    cannot even spell clearance/capacity/a second module), these two files enforce
    the semantic half (root uniqueness, unknown-target refusal, additive-only merge)
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/strata/_design_load.py
  reason: the extend-only fragment mechanism (module frob { } root closure, part-of
    fragment header, extend node { } merge) is a cross-file concept by definition
    -- one-root enforcement, unknown-root/unknown-node refusal, and the append-only
    never-weaken merge of extend grants against the root's already-elaborated grants
    structurally live in the existing T-1196 cross-file join (_multifile.py::elaborate_merged)
    and its loader caller (_design_load.py), not in the single-file grammar/AST layer
    alone; grammar+AST (declared scope) enforce the syntactic half (extend blocks
    cannot even spell clearance/capacity/a second module), these two files enforce
    the semantic half (root uniqueness, unknown-target refusal, additive-only merge)
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/strata/surface.md
  reason: 'surface.md is the parser/AST doc home every existing frob:doc anchor in
    scope already targets; the new module/part-of/extend grammar needs a #fragments
    section there'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/strata/test_fragments.py
  reason: new evidence file for the T-2502 fragment mechanism positive/negative controls
  actor: logan
  at: '2026-08-18'
- op: add
  glob: editors/vscode-strata/syntaxes/strata.tmLanguage.json
  reason: test_construct_keywords_match_parser_bidirectionally (tests/unit/test_strata_tmlanguage.py,
    already in this repo's touched-set test selection) drift-locks the syntax-highlighting
    grammar's declaration-keywords against strata-core/src/parse's construct dispatch;
    adding 'part'/'extend' to the parser trips this pre-existing lock and must be
    fixed in the same change, not left red (the file's own 'exclusive' clause-keyword
    gap is unrelated pre-existing debt, left untouched)
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/guides/extending/strata-surface-grammar.md
  reason: 'AFFECT001: Parser.parse_program (grammar_policy.rs) is this ticket''s own
    affects()-closure target for this doc per an existing frob:describes edge; adding
    the part/extend construct keywords to parse_program''s dispatch table requires
    touching this doc in the same diff or the gate refuses'
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/strata/test_fragments.py::TestParseFragmentGrammar::test_part_of_parses
- tests/unit/strata/test_fragments.py::TestParseFragmentGrammar::test_root_has_no_part_of
- tests/unit/strata/test_fragments.py::TestParseFragmentGrammar::test_fragment_cannot_declare_module
- tests/unit/strata/test_fragments.py::TestParseFragmentGrammar::test_fragment_cannot_declare_new_node
- tests/unit/strata/test_fragments.py::TestParseFragmentGrammar::test_extend_cannot_set_clearance
- tests/unit/strata/test_fragments.py::TestParseFragmentGrammar::test_extend_grant_requires_via
- tests/unit/strata/test_fragments.py::TestResolveFragments::test_widens_existing_grant
- tests/unit/strata/test_fragments.py::TestResolveFragments::test_extend_takes_effect_through_elaborate_merged
- tests/unit/strata/test_fragments.py::TestResolveFragments::test_no_root_is_error
- tests/unit/strata/test_fragments.py::TestResolveFragments::test_two_roots_is_error
- tests/unit/strata/test_fragments.py::TestResolveFragments::test_unrelated_multi_module_merge_is_unaffected
- tests/unit/strata/test_fragments.py::TestResolveFragments::test_unknown_root_name_is_error
- tests/unit/strata/test_fragments.py::TestResolveFragments::test_unknown_node_is_error
- tests/unit/strata/test_fragments.py::TestResolveFragments::test_unknown_atom_is_error
- tests/unit/strata/test_fragments.py::TestResolveFragments::test_single_file_design_passes_through_unchanged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: d520179c0ea490807f30489e07313dd58fc3cec5
---
`design/frob.strata` is 2276 lines / 188KB and there is exactly one of
it. Three single lines exceed 5KB (the testsuite node's exec / fs.read /
fs.write via-lists; the largest is 13,479 characters), so every agent
that adds a test file edits the same enormous line. That is a merge
conflict generator and the source of the recurring SELFAUDIT001 ratchet
bumps.

The grammar has NO include/import today (checked: no such keyword in
strata-core/src/parse/). Add one, with the explicit constraint that it
must be IMPOSSIBLE to break a system into pieces that stand alone:

- ONE CLOSURE ROOT. `module frob { ... }` may be declared in exactly one
  file. That declaration IS the system boundary; everything provable is
  proved against it.
- FRAGMENTS EXTEND, THEY DO NOT STAND ALONE. Another file says
  `part of frob` and may only EXTEND declared nodes
  (`extend node testsuite { ... }`). It may not declare a module, may not
  introduce a node the root does not know about, and is meaningless when
  loaded by itself.
- THE LOADER GLOBS, IT DOES NOT INCLUDE. `design/**/*.strata` is read as
  one unit. Exactly one root must exist; a fragment naming a nonexistent
  root is a hard error. There is no textual include, so no one can
  assemble a DIFFERENT system by including different files.

This is Rust's `mod` (files are organizational, the crate is the unit),
not C's `#include` (textual, no closure).

HARD CONSTRAINT: a fragment must never be able to WEAKEN a root
declaration. Extend-only, never override. Otherwise a fragment becomes a
place to quietly grant a capability the root refused -- the
exemption-that-disables-the-guard failure this repo has already paid for
once (T-1967).

Do not mandate modularity: the root may stay whole for anyone who wants
it whole. The point is that mechanically-accumulated content can move out
of the hand-authored design.