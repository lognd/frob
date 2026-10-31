+++
id = "01M64VBRFWT0EKCG800ANRZDTE"
title = "CAP: capability detection for Java (audit j01), import-resolved"
type = "story"
category = "in-progress"
priority = "high"
points = 8
reporter = "lognd"
created = "2026-10-29T22:09:20Z"
updated = "2026-10-31T02:22:46Z"
scope = ["crates/gob-languages/**", "crates/gob-symbols/**", "crates/grimble-check/tests/symbolic_audit.rs", "crates/gob-caps/**", "crates/grimble-bind/src/caps.rs", "crates/gob-plan/src/catalog/answer.rs", "docs/reference/languages.md", "docs/reference/grl/catalog.md", "Cargo.toml", "Cargo.lock", "crates/gob-symbols/tests/**"]

[[acceptance]]
text = "Java is a supported language (grammar, detect) with an import-resolved scanner reporting single-type, wildcard, static and fully qualified uses of ProcessBuilder, Runtime.exec, java.io, java.nio.file, java.net, HttpClient, System.getenv, reflection and ClassLoader."
bound = true

[[acceptance]]
text = "Audit case j01 is pinned as a regression test in crates/grimble-check/tests/symbolic_audit.rs and unresolvable forms report Unresolved."
bound = false
+++

Split from PKW7X2J. Java has no Language variant or grammar. Needs: grammar plus detect, import-resolved scanner (single-type, wildcard, static imports, fully qualified names), vocab for ProcessBuilder, Runtime.exec, java.io/java.nio.file, java.net, HttpClient, System.getenv, reflection and ClassLoader. Pin audit case j01.
