+++
id = "01M4CTTWD4YG8CKEX9FW1F0AP5"
title = "A fresh repository's frob check prints no Unresolved lines that come from frob's own defaults"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4CTTPJ00PTDE0A1SE4MJFCF"
reporter = "lognd"
created = "2026-10-08T04:02:39Z"
updated = "2026-10-08T04:02:39Z"
scope = ["changelog.d/**", "crates/frob-check/**", "crates/frob/**", "crates/gob-check/**"]

[[acceptance]]
text = "Given frob init in an empty repository, when frob check runs, then it reports no Unresolved finding"
bound = false
+++

notes/review/adoption-trial-2026-10-07.md MEDIUM: 7 Unresolved lines on a fresh check trace to frob's own frob.toml defaults and .gitattributes.
