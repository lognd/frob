+++
id = "01M5HYRXMB54SZ7KN3W6EQFB65"
title = "Orphan ticket branch .gitattributes gets no tickets eol=lf pin under core.autocrlf"
type = "task"
category = "todo"
priority = "low"
points = 3
reporter = "lognd"
created = "2026-10-22T14:03:23Z"
updated = "2026-10-22T16:45:17Z"
scope = ["crates/frob-ledger/**", "changelog.d/**"]

[[acceptance]]
text = "Given core.autocrlf=true and an orphan ticket branch, when frob init or ledger setup runs, then the branch .gitattributes carries tickets/** text eol=lf and a second run changes nothing"
bound = false
+++

Follow-up of GEKVBBH: the ticket branch .gitattributes is generated in crates/frob-ledger/src/layout.rs and is not pinned to eol=lf when core.autocrlf=true.
