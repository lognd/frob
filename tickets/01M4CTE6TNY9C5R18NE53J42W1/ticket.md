+++
id = "01M4CTE6TNY9C5R18NE53J42W1"
title = "Config Document: parse frob.toml once per command; move [tickets] and git tables into frob-ledger with one parser (audit M13)"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T03:55:44Z"
updated = "2026-10-08T03:55:44Z"
scope = ["changelog.d/**", "crates/gob-config/**", "crates/frob-ledger/**", "crates/frob/**", "crates/frob-*/src/config.rs"]

[[acceptance]]
text = "Given any frob verb, when it runs, then frob.toml is read once (counter test)"
bound = false

[[acceptance]]
text = "Given [tickets], when parsed, then exactly one parser in frob-ledger owns it"
bound = false
+++

notes/review/audit-2026-10-07.md M13: four [tickets] parsers, FrobConfig::load re-reads frob.toml 11 times per command.
