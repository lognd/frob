+++
id = "01M44YQSHSC4N13E98FN2HND27"
title = "gob-languages: C# grammar and comment scanners"
type = "story"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-05T02:36:57Z"
updated = "2026-10-05T03:38:26Z"
idempotency_key = "d94-lang"
scope = ["crates/gob-languages/**", "crates/gob-directives/src/comments.rs", "crates/gob-directives/src/scan.rs", "crates/frob-obligations/src/comments.rs", "docs/reference/directives.md", "docs/reference/fidelity.md", "Cargo.toml", "Cargo.lock"]

[[acceptance]]
text = "Given a C# file with a frob directive in a // comment and a bare TODO in a /// comment, when frob check runs, then the directive binds to the member below and TODO001 fires"
bound = true

[[acceptance]]
text = "Given a C# string literal (regular, verbatim, interpolated, raw) containing // or /*, when the comment scanners run, then no comment is reported inside the string"
bound = true

[[acceptance]]
text = "Given a C# file with a syntax error, when it is parsed, then the partial tree is reported as a parse gap and never as an empty clean file"
bound = true
+++

Language::CSharp (.cs, .csx excluded; .cs only) in crates/gob-languages (language.rs, grammar.rs, parse.rs, comments.rs, query.rs): tree-sitter-c-sharp pinned the way the Rust and Python grammars are (grammar_version recorded for the cache key, hash.rs). Both comment scanners learn C# comment syntax: `//`, `///` XML doc lines, block and `/** */` comments, honoring verbatim, interpolated and raw string literals so a `//` inside a string is not a comment. That makes frob directives, accepts and TODO001 work in C# files. Preprocessor lines (#if, #region) are not comments but must not break scanning. Docs: docs/reference/directives.md (C# comment forms), docs/reference/fidelity.md language list. Same files as ~17ZVW3R (TS/TSX/CSS grammars): sequence or coordinate leases, do not both edit comments.rs at once.
