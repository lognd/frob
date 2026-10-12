+++
id = "01M4CTE0GYDX0XW64JRNF2ZMQG"
title = "gob-walk stops depending on gob-git: file-reader trait in gob-walk, gob-git implements it; drop gob-lock -> gob-ir and gob-cache -> gob-exec (audit M8)"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T03:55:37Z"
updated = "2026-10-12T20:35:43Z"
scope = ["changelog.d/**", "crates/gob-walk/**", "crates/gob-git/**", "crates/gob-lock/**", "crates/gob-cache/**", "crates/gob-ir/**", "crates/gob-exec/**", "Cargo.lock", "crates/frob/src/main.rs", "crates/gob-dev/src/main.rs", "crates/gob-dev/tests/layering.rs", "crates/grimble/src/main.rs", "crates/frob-check/**", "crates/frob-ack/**", "crates/frob-lease/**", "crates/frob-obligations/**", "crates/grimble-check/**", "crates/gob-config/**"]

[[acceptance]]
text = "Given cargo tree -p gob-walk, gob-ir, gob-symbols and grimble-model, when inspected, then no gix crate appears (test over cargo metadata)"
bound = true

[[acceptance]]
text = "Given the workspace, when the full suite runs, then it passes"
bound = true
+++

notes/review/audit-2026-10-07.md M8. gix (54 crates) sits under gob-ir, gob-symbols, grimble-model and crunk-check and on the critical path of every binary. Also stop gob-walk reading frob.toml (M9 list). Merge with the canonical/common-dir move named in the audit if ~ARHP82G is not started.
