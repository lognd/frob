## Done report

gob-directives and the Directive derive per code-model.md section 4, D24 and D32: derive generates parse_args, a const DirectiveMeta (args as a static slice with key, list, ticket_ref flags and per-field summaries) registered in inventory and a runtime JSON schema; Scanner over Rust comments via the tree, markdown HTML comments and TOML hash comments with a plain-text fallback; grammar namespace:verb args with quoted values; binding: next symbol within 2 lines, else enclosing symbol, else file; markdown and inner doc comments bind to the enclosing section or file; frob:tests reorientation from test items with the enclosing test kept as source; PARSE001, DSL001 (did-you-mean) and DSL002 (abbreviated ticket id, remedy frob ticket expand); milestone-1 directive structs ticket, todo, doc, tests, invariant, accept, defer; mdtest corpora with fire and clean blocks in rust, markdown and toml; trybuild cases. Deviations: scan_in takes a FileId; a directive must start a comment line; findings suppress the record; Defer uses because= (exceptions.md example says reason=, to reconcile in T-0029); [directives] namespaces not yet a ConfigTable.

### Changed
```
 Cargo.lock                                         |  21 ++
 crates/gob-directives/Cargo.toml                   |  31 ++
 crates/gob-directives/src/args.rs                  | 303 ++++++++++++++++++
 crates/gob-directives/src/bind.rs                  | 110 +++++++
 crates/gob-directives/src/comments.rs              | 265 +++++++++++++++
 crates/gob-directives/src/frob.rs                  | 106 ++++++
 crates/gob-directives/src/lex.rs                   | 187 +++++++++++
 crates/gob-directives/src/lib.rs                   |  57 ++++
 crates/gob-directives/src/meta.rs                  | 118 +++++++
 crates/gob-directives/src/rules.rs                 |  57 ++++
 crates/gob-directives/src/scan.rs                  | 354 +++++++++++++++++++++
 crates/gob-directives/src/ulid.rs                  |  68 ++++
 crates/gob-directives/tests/common/mod.rs          |  34 ++
 crates/gob-directives/tests/corpus.rs              |  13 +
 crates/gob-directives/tests/derive.rs              |  90 ++++++
 crates/gob-directives/tests/mdtest/dsl001.md       |  40 +++
 crates/gob-directives/tests/mdtest/dsl002.md       |  46 +++
 crates/gob-directives/tests/mdtest/parse001.md     | 107 +++++++
 crates/gob-directives/tests/scan.rs                | 275 ++++++++++++++++
 crates/gob-macros/Cargo.toml                       |   3 +-
 crates/gob-macros/src/directive.rs                 | 341 ++++++++++++++++++++
 crates/gob-macros/src/lib.rs                       |  24 +-
 crates/gob-macros/tests/ui.rs                      |   2 +-
 crates/gob-macros/tests/ui/directive_bad_order.rs  |  15 +
 .../gob-macros/tests/ui/directive_bad_order.stderr |  11 +
 .../gob-macros/tests/ui/directive_list_not_vec.rs  |  11 +
 .../tests/ui/directive_list_not_vec.stderr         |   5 +
 .../tests/ui/directive_missing_namespace.rs        |  11 +
 .../tests/ui/directive_missing_namespace.stderr    |   7 +
 crates/gob-macros/tests/ui/directive_no_doc.rs     |  10 +
 crates/gob-macros/tests/ui/directive_no_doc.stderr |   7 +
 tickets/T-0014/ticket.md                           |   6 +-
 32 files changed, 2727 insertions(+), 8 deletions(-)
```

### Evidence
(no evidence recorded)
