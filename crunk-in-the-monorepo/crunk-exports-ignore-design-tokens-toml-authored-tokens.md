+++
id = "01M5XK12082GJW5KQTMK4DJXGN"
title = "crunk exports ignore design/tokens/*.toml: authored tokens never reach CSS, Tailwind, USS or C#"
type = "bug"
category = "todo"
priority = "medium"
points = 2
parent = "01M4CXQTERP5YASZGVEAH6KG4H"
reporter = "lognd"
created = "2026-10-27T02:29:00Z"
updated = "2026-10-27T02:58:43Z"
scope = ["crates/crunk-tokens/src/**,crates/crunk/src/tokens.rs,crates/crunk/src/export.rs"]
+++

Found while working ~7YXEHNJ. TokenSet::from_spec renders crunk.toml only; design/tokens/*.toml is read by the TOKEN lints (crunk-rules token_files) but no exporter merges it, so a palette moved into design/tokens does not drive the exports. Also tokens --check names files, not tokens; the token-naming drift comes from EXPORT002 via crunk check.
