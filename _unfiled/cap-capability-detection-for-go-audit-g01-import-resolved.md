+++
id = "01M64VBRCNYQ3WC895EYXR6GME"
title = "CAP: capability detection for Go (audit g01), import-resolved"
type = "story"
category = "in-progress"
priority = "high"
points = 8
reporter = "lognd"
created = "2026-10-29T22:09:20Z"
updated = "2026-10-31T01:21:28Z"
scope = ["crates/gob-languages/**", "crates/gob-symbols/**", "crates/grimble-check/tests/symbolic_audit.rs", "Cargo.toml", "Cargo.lock", "crates/grimble-bind/src/caps.rs", "crates/gob-caps/**", "crates/gob-plan/src/catalog/answer.rs"]

[[acceptance]]
text = "Go is a supported language (grammar, detect) and an import-resolved scanner reports aliased, dot-import and package-qualified uses of os/exec, os, net, net/http, os.Getenv and plugin as capability uses"
bound = false

[[acceptance]]
text = "Audit case g01 is pinned as a regression test in crates/grimble-check/tests/symbolic_audit.rs, and unresolvable forms report Unresolved, never silent"
bound = false
+++

Split from PKW7X2J. Go has no Language variant or tree-sitter grammar in gob-languages, so no resolved path-use scanner or VocabEntry rows exist. Needs: grammar plus detect, import-resolved scanner (aliases, dot imports, package-qualified names) in gob-symbols lookups, vocab for os/exec, os, net, net/http, os.Getenv, plugin. Pin audit case g01. Unresolvable forms report Unresolved.
