+++
id = "01M4M52WDAB9VH3PJ2VDF2JFRY"
title = "Move DIGEST_SCHEME into gob-caps and drop gob-lock -> gob-ir (audit M8 slice)"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4CTE0GYDX0XW64JRNF2ZMQG"
reporter = "lognd"
created = "2026-10-11T00:16:28Z"
updated = "2026-10-11T00:17:42Z"
scope = ["crates/gob-caps/**,crates/gob-lock/**,crates/gob-ir/**,crates/gob-symbols/**,crates/grimble-check/**,changelog.d/**"]

[[acceptance]]
text = "Given cargo metadata, when the gob-lock package's normal dependencies are listed, then gob-ir is not among them (test gob_lock_does_not_depend_on_gob_ir)"
bound = false

[[acceptance]]
text = "Given the gob-caps constant, when compared with gob_ir::DIGEST_SCHEME and gob_lock::DIGEST_SCHEME, then all three are the same value (test digest_scheme_is_one_constant)"
bound = false
+++

Split from ~NF2ZMQG. gob-lock depends on gob-ir for one u32 (gob-lock/src/file.rs:18). Define the constant in gob-caps and re-export it from gob-ir and gob-symbols so grimble-check keeps compiling. Acceptance: cargo metadata shows no gob-lock -> gob-ir edge.
