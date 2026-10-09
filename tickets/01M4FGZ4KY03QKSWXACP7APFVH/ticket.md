+++
id = "01M4FGZ4KY03QKSWXACP7APFVH"
title = "vmodel runnables: several runner ids or manual per test, and derivable TS and Rust selectors"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T05:07:56Z"
updated = "2026-10-09T05:08:20Z"
idempotency_key = "logand-gaps-V3"
labels = ["adoption:logand-app", "grimble"]
scope = ["crates/grimble-bind/**", "crates/gob-languages/**", "crates/grimble-model/**", "changelog.d/**"]

[[links]]
kind = "blocked-by"
target = "01M4FGZ22EX779T6RNS4FKJ689"

[[acceptance]]
text = "Given a test with several runnable ids, when grimble check runs, then there is no SYS003 and each id binds"
bound = false

[[acceptance]]
text = "Given a manual test, when grimble check runs, then no MDL014 and no MDL005, and it is listed as manual"
bound = false

[[acceptance]]
text = "Given a vitest test under web/ and a cargo test, when referenced by the documented selector, then each binds and a wrong id in an existing file names the nearest real id"
bound = false
+++

Repros 13 (~/projects/frob-v2-repros/logand-grimble-20261009/13-vmodel-runnable-one-or-manual) and 14 (~/projects/frob-v2-repros/logand-grimble-20261009/14-vmodel-ts-rust-runnable-names). Implements the vmodel docs decision. The 13 acceptance on verified_by arms is amended on planning ticket ~D4J3YZ2 (P4).
