+++
id = "01M5XK12082GJW5KQTMK4DJXGN"
title = "crunk exports ignore design/tokens/*.toml: authored tokens never reach CSS, Tailwind, USS or C#"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M4CXQTERP5YASZGVEAH6KG4H"
reporter = "lognd"
created = "2026-10-27T02:29:00Z"
updated = "2026-11-14T13:09:42Z"
scope = ["crates/crunk-tokens/src/**,crates/crunk/src/tokens.rs,crates/crunk/src/export.rs", "crates/crunk-tokens/src/export/mod.rs", "crates/crunk-tokens/tests/it/design_tokens_export.rs"]

[[acceptance]]
text = "tokens --target and export css|tailwind|uss|csharp render the authored design/tokens tokens"
bound = true
+++

Found while working ~7YXEHNJ. TokenSet::from_spec renders crunk.toml only; design/tokens/*.toml is read by the TOKEN lints (crunk-rules token_files) but no exporter merges it, so a palette moved into design/tokens does not drive the exports. Also tokens --check names files, not tokens; the token-naming drift comes from EXPORT002 via crunk check.
