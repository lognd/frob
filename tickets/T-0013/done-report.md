## Done report

gob-symbols per code-model.md sections 2-3 and D31: Symref grammar for path::Qual.Name and path#slug, SymbolKind, Visibility, three-facet blake3 digests over whitespace-collapsed facet text, Rust extraction by direct tree-sitter tree walking (modules, fns, methods, structs, enums, variants, traits, impls as Type[Trait], consts, statics, type aliases, macros), markdown headings with GitHub slugging, import edges, conservative call graph with Resolved/Ambiguous/Unresolved edges, petgraph SymbolGraph with public_api, affects, reach, graph_digest, resolve with suffix matching, rayon pipeline with postcard payloads cached in gob-cache keyed by content digest and extractor plus grammar identity; corpus tests and a criterion bench (about 16 ms over crates/). Known gaps recorded in the done-report: setext headings, nested items, struct fields, receiver-typed method resolution, bare use paths treated as external. Deviations: own FacetDigest type pending Digest::from_bytes in gob-walk; file-level Module nodes per file; span is a file-local TextRange; impl members carry an implements field.

### Changed
```
 Cargo.lock                                         | 105 ++++
 crates/gob-symbols/Cargo.toml                      |  35 ++
 crates/gob-symbols/benches/graph.rs                |  24 +
 crates/gob-symbols/src/graph.rs                    | 532 ++++++++++++++++
 crates/gob-symbols/src/lib.rs                      |  45 ++
 crates/gob-symbols/src/markdown.rs                 | 159 +++++
 crates/gob-symbols/src/model.rs                    | 202 ++++++
 crates/gob-symbols/src/paths.rs                    |  50 ++
 crates/gob-symbols/src/pipeline.rs                 | 145 +++++
 crates/gob-symbols/src/rust.rs                     | 682 +++++++++++++++++++++
 crates/gob-symbols/src/symref.rs                   | 240 ++++++++
 .../tests/corpus/markdown/basic.expected           |   6 +
 crates/gob-symbols/tests/corpus/markdown/basic.md  |  27 +
 .../gob-symbols/tests/corpus/rust/basic.expected   |  26 +
 crates/gob-symbols/tests/corpus/rust/basic.rs      |  76 +++
 crates/gob-symbols/tests/symbols.rs                | 329 ++++++++++
 tickets/T-0013/ticket.md                           |   6 +-
 17 files changed, 2686 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)
