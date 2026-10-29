+++
id = "01M64VBRFWT0EKCG800ANRZDTE"
title = "CAP: capability detection for Java (audit j01), import-resolved"
type = "story"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-10-29T22:09:20Z"
updated = "2026-10-29T22:09:20Z"
scope = ["crates/gob-languages/**", "crates/gob-symbols/**"]
+++

Split from PKW7X2J. Java has no Language variant or grammar. Needs: grammar plus detect, import-resolved scanner (single-type, wildcard, static imports, fully qualified names), vocab for ProcessBuilder, Runtime.exec, java.io/java.nio.file, java.net, HttpClient, System.getenv, reflection and ClassLoader. Pin audit case j01.
