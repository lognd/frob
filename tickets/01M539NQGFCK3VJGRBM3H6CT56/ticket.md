+++
id = "01M539NQGFCK3VJGRBM3H6CT56"
title = "GRL examples: NEAT013 example 0 needs python import resolution onto the clock vocab (time.time)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-16T21:25:16Z"
updated = "2026-10-16T23:50:59Z"
scope = ["crates/gob-plan/**", "crates/gob-symbols/**"]

[[acceptance]]
text = "NEAT013 examples all pass, with python time.time resolving to a unit in the clock vocab"
bound = true

[[acceptance]]
text = "External ambient units and the python ambient vocab are covered by unit tests"
bound = false
+++

Split from ~C6ZSWB2: 'c resolves to v' for python time.time must yield a unit in the clock vocab. Remove NEAT013 0 from KNOWN_ENGINE_GAPS.
