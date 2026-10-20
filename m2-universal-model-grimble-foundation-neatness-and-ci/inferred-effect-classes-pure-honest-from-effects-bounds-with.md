+++
id = "01M4CXT1GFPWZAMV0BCBH3WC4G"
title = "Inferred effect classes (pure, honest) from effects Bounds with may-alias, and NEAT037 effect-row-widening against the base"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CXSN7VTEYX5AVSZVDX2WPZ"
reporter = "lognd"
created = "2026-10-08T04:54:37Z"
updated = "2026-10-08T04:54:37Z"
scope = ["changelog.d/**", "crates/gob-ir/**", "crates/grimble-check/**"]

[[acceptance]]
text = "Given a helper inferred pure on the base, when a change makes it read the clock, then NEAT037 fires with no annotation present"
bound = false

[[acceptance]]
text = "Given an FFI boundary with grimble:effects none, when callers are checked, then their classes resolve and the claim itself is reported UNVERIFIED"
bound = false
+++

docs/design/cohesion.md 5 (D121): inference first; claims only at boundaries and public contracts; NEAT011 only for public units whose class is Unknown.
