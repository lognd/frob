+++
id = "01M6RHBVHQBW025N2RNM6ZVE60"
title = "COH004 corpus: fire example once the rule can fail"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-11-06T13:39:26Z"
updated = "2026-11-13T08:12:09Z"
labels = ["no-story", "good-first"]
scope = ["crates/grimble-check/**"]

[[acceptance]]
text = "Given the COH004 corpus page, when the corpus runs, then an expect=fire example fires and passes."
bound = false
+++

COH004 reports Unresolved only, so its page has no expect=fire example.

## Start here

See crates/grimble-check COH004 rule and its corpus page; add a firing example once the rule can fail.
