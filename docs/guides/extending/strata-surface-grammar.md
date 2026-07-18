# Strata surface grammar keywords

<!-- frob:describes strata-core/src/parse.rs::Parser.parse_program -->

## What it is and where it lives

The `.strata` design-file surface grammar is a hand-written recursive
descent parser in `strata-core/src/parse.rs` (Rust, compiled via PyO3 into
`strata_core`, see `make core`). Top-level declaration keywords (`node`,
`flow`, `boundary`, `scenario`, `claim`, `deploy`, `managed`, `abstract`,
`observe`, ...) are dispatched in `Parser::parse_program`; keyword
matching within a construct goes through `Parser::expect_keyword`. The
SAME keyword vocabulary is hand-spelled a second time, for syntax
highlighting only, in `editors/vscode-strata/syntaxes/strata.tmLanguage.json`
(T-0139) -- this is the one registry in this series with a THIRD artifact
(an editor grammar file) that must track the parser, not just a doc.

## Add-an-entry recipe (new keyword)

1. Add the keyword to `parse_program`'s top-level dispatch (or the
   relevant construct's field parser) in `strata-core/src/parse.rs`.
2. Add the SAME keyword string to
   `editors/vscode-strata/syntaxes/strata.tmLanguage.json`'s keyword
   pattern list -- this is a hand-edit, not generated.
3. Run `make core` to rebuild `strata_core` with the new parser.
4. Add a parser unit test in `strata-core`'s own test module (`cargo test
   --lib`, see [`[[test.runner]]` entries](test-runner-entries.md)) and a
   `.strata` fixture exercising the new construct if it introduces new
   surface syntax beyond a bare keyword.
5. Document the new keyword in `docs/strata/surface.md`.

## Drift-locks that fire

- `tests/unit/test_strata_tmlanguage.py`: extracts the parser's top-level
  declaration keyword set (regex over `parse.rs`) and the grammar's
  keyword set (`json.load` over the `.tmLanguage.json` file) and asserts
  they agree BIDIRECTIONALLY -- a keyword added to the parser without a
  matching grammar update, or a stray keyword left in the grammar after a
  parser change, fails this test. This is the drift-lock's entire job;
  there is no other automated check tying the two files together.
- `frob check`'s SYS family does not itself parse `.strata` surface
  syntax -- keyword drift is caught ONLY by the tmLanguage test above,
  not by a `frob check` gate.

## Worked example diff

The `managed` marker (external-infrastructure nodes with no tier-2
refinement, `docs/strata/surface.md`): added to `parse_program`'s node
modifier dispatch in `parse.rs`, then the literal string `"managed"`
added to `strata.tmLanguage.json`'s keyword alternation, `make core` run
to pick up the change, and `docs/strata/surface.md`'s node-decl grammar
table gained the row. `test_strata_tmlanguage.py` would have failed
(parser-only keyword) had the grammar-file half been skipped.

## Common mistakes

- **Editing `parse.rs` and forgetting `make core`.** The Python-side
  tests import the COMPILED `strata_core` wheel, not the Rust source
  directly -- a parser change with no rebuild is invisible to every
  Python-side test, not just the tmLanguage drift-lock. See
  `docs/guides/agent-playbook.md` section 1 (worktree warm-up) for the
  same lesson at the whole-repo level.
- **Editing only one of the two keyword lists.** Both directions of the
  drift-lock fire independently -- a keyword removed from the parser but
  left in the grammar fails just as loudly as the reverse, since stale
  highlighting for a construct that no longer parses is its own bug.

## See also

- `docs/strata/surface.md` -- full surface grammar reference.
- [Prover claim kinds](prover-claim-kinds.md) and
  [Scenario kinds](scenario-kinds.md) -- both require a matching
  `parse.rs` production for any new claim/rewrite shape to be authorable
  directly in `.strata` source.
