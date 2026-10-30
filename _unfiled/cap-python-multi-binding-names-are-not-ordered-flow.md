+++
id = "01M65H96VGNFJW5GY8BVMAW61Q"
title = "CAP: Python multi-binding names are not ordered flow-sensitively"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-30T04:32:25Z"
updated = "2026-10-30T04:32:25Z"
scope = ["crates/gob-symbols/**", "crates/grimble-bind/**"]
+++

found while working 7XKRQQ2: an import followed by a dead rebinding is reported unresolved; x = run of a multiply bound name is not followed
