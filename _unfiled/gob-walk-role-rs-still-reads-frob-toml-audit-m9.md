+++
id = "01M55VA2AK0NWCPD6H688GE28M"
title = "gob-walk role.rs still reads frob.toml (audit M9)"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-17T21:11:58Z"
updated = "2026-10-27T02:58:21Z"
scope = ["crates/gob-walk/**"]
+++

found while working ~NF2ZMQG: Roles::for_root and ledger_dir read frob.toml in gob-walk.
