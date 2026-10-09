+++
id = "01M4FGYNKKP10PVPT90AKKMHBY"
title = "Finding floods: SYS003 end-owner once per clause, MDL005 once per selector"
type = "bug"
category = "todo"
priority = "medium"
points = 3
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T05:07:41Z"
updated = "2026-10-09T05:07:41Z"
idempotency_key = "logand-gaps-F1"
labels = ["adoption:logand-app", "grimble"]
scope = ["crates/grimble-bind/**", "crates/grimble-check/**", "crates/grimble-model/**", "changelog.d/**"]

[[acceptance]]
text = "Given consumer pkg/** owned by the wrong node over 7 units, when grimble check runs, then one SYS003 names the clause, the count 7 and a bounded sample of units"
bound = false

[[acceptance]]
text = "Given selector future3/** written in three clauses, when grimble check runs, then one MDL005 per distinct selector listing the clause sites"
bound = false

[[acceptance]]
text = "Given check --json, when read, then the per-unit detail is still present"
bound = false
+++

Repros 17-sys003-end-owner-flood (~/projects/frob-v2-repros/logand-grimble-20261009/17-sys003-end-owner-flood) and 21-design-first-warning-flood (~/projects/frob-v2-repros/logand-grimble-20261009/21-design-first-warning-flood). One wrong consumer glob gives one SYS003 per unit (51 findings for a 10-file package); the same missing path warns once per clause (167 MDL005 on the model, 139 vmodel runnables). Group by clause with a count and a bounded sample; keep every unit in check --json.
