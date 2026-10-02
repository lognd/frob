## Done report

gob-languages per code-model.md sections 3 and 8: tree-sitter core 0.27.0 with tree-sitter-rust 0.24.2, tree-sitter-md 0.5.3, tree-sitter-toml-ng 0.7.0 pinned exactly (all only depend on tree-sitter-language 0.1); ast-grep-core 0.45.3 requires tree-sitter 0.27.0 so it is compatible, closing audit M26's version question. Language enum always present with GrammarUnavailable when a feature is off; ParseLimits with size cap and progress-callback timeout returning Unresolved rather than panicking; grammar_identity string lang:crate@ver:abiN:tsCore with a test tying it to the Cargo.toml pins; compiled query cache in a OnceLock; captures collected eagerly. Deviations: identity uses the exact pin and ABI rather than a grammar content hash; captures are eager.

### Changed
```
 Cargo.lock                           | 381 +++++++++++++++++++++++++++++++++++
 crates/gob-languages/Cargo.toml      |  30 +++
 crates/gob-languages/src/grammar.rs  |  87 ++++++++
 crates/gob-languages/src/language.rs |  63 ++++++
 crates/gob-languages/src/lib.rs      |  49 +++++
 crates/gob-languages/src/parse.rs    | 232 +++++++++++++++++++++
 crates/gob-languages/src/query.rs    | 198 ++++++++++++++++++
 tickets/T-0012/ticket.md             |   6 +-
 8 files changed, 1043 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)
