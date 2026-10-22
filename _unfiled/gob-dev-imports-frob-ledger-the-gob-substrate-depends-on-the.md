+++
id = "01M48NCNDQZ27NP0JQ7M8WETW7"
title = "gob-dev imports frob-ledger: the gob substrate depends on the frob goblin (SYS013 layering inversion)"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-06T13:10:29Z"
updated = "2026-10-22T05:16:52Z"
scope = ["crates/gob-dev/**", "design/model.grmb", "crates/frob-ledger/Cargo.toml", "crates/frob-ledger/benches", "crates/frob-ledger/src", "crates/frob-ledger/templates", "crates/frob-ledger/tests", "Cargo.lock", "changelog.d/01M48NCNDQZ27NP0JQ7M8WETW7.changed.md"]

[[acceptance]]
text = "gob-dev no longer imports frob-ledger or any frob crate (cargo tree -p gob-dev shows none) and SYS013 reports no gob->frob edge from crates/gob-dev"
bound = false

[[acceptance]]
text = "the gob -> frob flow in design/model.grmb citing this ticket is removed and the import_v1 behaviour tests still pass"
bound = false
+++

found while working ~FS8AX88. SYS013 reports 15 call edges from node gob (crates/gob-dev/src/import_v1.rs) into node frob (crates/frob-ledger). design/model.grmb declares the flow gob -> frob citing this ticket; remove it when gob-dev stops importing frob crates, or move gob-dev out of node gob.
