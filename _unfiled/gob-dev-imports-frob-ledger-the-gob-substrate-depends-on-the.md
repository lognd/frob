+++
id = "01M48NCNDQZ27NP0JQ7M8WETW7"
title = "gob-dev imports frob-ledger: the gob substrate depends on the frob goblin (SYS013 layering inversion)"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-06T13:10:29Z"
updated = "2026-10-06T13:10:29Z"
scope = ["crates/gob-dev/**"]
+++

found while working ~FS8AX88. SYS013 reports 15 call edges from node gob (crates/gob-dev/src/import_v1.rs) into node frob (crates/frob-ledger). design/model.grmb declares the flow gob -> frob citing this ticket; remove it when gob-dev stops importing frob crates, or move gob-dev out of node gob.
