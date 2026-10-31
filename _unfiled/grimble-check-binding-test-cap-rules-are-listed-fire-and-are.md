+++
id = "01M68W8MN41YVVYTXA0TBXYWWK"
title = "grimble-check binding test cap_rules_are_listed_fire_and_are_writable_in_accept fails on experimental (MDL013 for may fs.write)"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-31T11:42:04Z"
updated = "2026-10-31T12:05:16Z"
scope = ["crates/grimble-check/**", "crates/grimble-model/**"]

[[acceptance]]
text = "cap_rules_are_listed_fire_and_are_writable_in_accept passes"
bound = false
+++

found while working ~8GS7YBF: the test fails identically without that change (findings include four MDL013 where accept CAP001/CAP002 with may fs.write is expected clean).
