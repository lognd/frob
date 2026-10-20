+++
id = "01M4M52WDAB9VH3PJ2VDF2JFRY"
title = "Move DIGEST_SCHEME into gob-caps and drop gob-lock -> gob-ir (audit M8 slice)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M4CTE0GYDX0XW64JRNF2ZMQG"
reporter = "lognd"
created = "2026-10-11T00:16:28Z"
updated = "2026-10-11T01:22:20Z"
scope = ["crates/gob-caps/**", "crates/gob-lock/**", "crates/gob-ir/**", "crates/gob-symbols/**", "crates/grimble-check/**"]

[[acceptance]]
text = "Given the gob-lock manifest, when its dependency tables are read, then gob-ir is in none of them and gob_lock::DIGEST_SCHEME equals gob_caps::DIGEST_SCHEME (test gob_lock_does_not_depend_on_gob_ir)"
bound = true

[[acceptance]]
text = "Given gob-ir, when its DIGEST_SCHEME is compared with gob-caps, then they are the same constant (test digest_scheme_is_one_constant)"
bound = true
+++

Split from ~NF2ZMQG. gob-lock depends on gob-ir for one u32 (gob-lock/src/file.rs:18). Define the constant in gob-caps and re-export it from gob-ir and gob-symbols so grimble-check keeps compiling. Acceptance: cargo metadata shows no gob-lock -> gob-ir edge.
