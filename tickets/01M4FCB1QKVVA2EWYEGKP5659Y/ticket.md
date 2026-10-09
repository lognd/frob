+++
id = "01M4FCB1QKVVA2EWYEGKP5659Y"
title = "Directives accept v1 ticket aliases: frob:todo T-#### and frob:ticket T-#### resolve through imported ticket aliases"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T03:47:03Z"
updated = "2026-10-09T05:24:38Z"
labels = ["adoption:hullbreach"]
scope = ["changelog.d/**", "docs/design/code-model.md", "crates/gob-directives/src/ulid.rs", "crates/gob-directives/src/scan.rs", "crates/gob-directives/tests/mdtest/dsl002.md", "crates/frob-obligations/src/refs.rs", "crates/frob-obligations/tests/mdtest/ref001.md"]

[[acceptance]]
text = "Given a ticket imported from v1 with alias T-0042, when a file carries frob:todo T-0042, then the directive resolves to that ticket with no finding, and an unknown T-#### is an unresolved-reference finding naming the alias"
bound = true
+++

Request from the hullbreach adoption (platform 130, game 116 v1 tickets): both repos use frob:todo T-#### throughout; v2 requires the 26-char ULID. Resolve v1 aliases from the ticket ledger's aliases field (set by the importer) instead of rewriting every file.
