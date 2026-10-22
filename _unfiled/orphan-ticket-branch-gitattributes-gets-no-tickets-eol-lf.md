+++
id = "01M5HYRXMB54SZ7KN3W6EQFB65"
title = "Orphan ticket branch .gitattributes gets no tickets eol=lf pin under core.autocrlf"
type = "task"
category = "done"
outcome = "done"
priority = "low"
points = 3
reporter = "lognd"
created = "2026-10-22T14:03:23Z"
updated = "2026-10-22T16:58:48Z"
scope = ["crates/frob-ledger/**", "changelog.d/**"]

[[acceptance]]
text = "Given an orphan ticket branch created under core.autocrlf=true, when frob init or ledger setup creates it, then its .gitattributes carries `*.md text eol=lf` and `*.toml text eol=lf` (the branch holds no tickets/ directory, so the pin covers ledger text by extension, unconditionally), and a second run changes nothing"
bound = true
+++

Follow-up of GEKVBBH: the ticket branch .gitattributes is generated in crates/frob-ledger/src/layout.rs and is not pinned to eol=lf when core.autocrlf=true.
