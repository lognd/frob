+++
id = "01M4M52WVPN2J5P3W4GPNE5PK9"
title = "gob-walk takes the ledger dir from the caller instead of reading frob.toml (audit M9 slice)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
parent = "01M4CTE0GYDX0XW64JRNF2ZMQG"
reporter = "lognd"
created = "2026-10-11T00:16:29Z"
updated = "2026-10-12T20:29:22Z"
scope = ["crates/gob-walk/**", "crates/frob-check/**", "crates/frob-ack/**", "crates/frob-lease/**", "crates/frob-obligations/**", "changelog.d/**"]
+++

Split from ~NF2ZMQG. gob-walk role.rs reads frob.toml [tickets] dir with a silent default. Make Roles::for_root take the dir; frob callers pass it. Acceptance: a gob-walk test showing no frob.toml read.
