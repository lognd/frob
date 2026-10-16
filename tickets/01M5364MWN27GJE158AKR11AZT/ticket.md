+++
id = "01M5364MWN27GJE158AKR11AZT"
title = "GRL constructs to express LAYER and ORG: crunk host input, class-selector kind, value-domain predicates, crunk.json side relations"
type = "story"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-16T20:23:31Z"
updated = "2026-10-16T21:49:52Z"

[[acceptance]]
text = "Given a string value, when a GRL rule tests it with is integer, then signed whole numbers hold and keywords such as auto, decimals and units do not"
bound = false
+++

Found while working ~C6A77WW. See packs/crunk-core/exceptions.toml on branch ticket/C6A77WW: every LAYER001/ORG001-005 is blocked by a named missing construct (int-parse value predicate, css class-selector node, per-file bucket attribute, glob membership over config.org columns, config.layers/org side relations typed from docs/schemas/crunk.json, gen rules target for a non-std pack with a CrunkHost).
