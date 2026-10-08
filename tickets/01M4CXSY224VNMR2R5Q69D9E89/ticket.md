+++
id = "01M4CXSY224VNMR2R5Q69D9E89"
title = "TypeScript type facts from tsc --strict as a bound tool"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CXSN7VTEYX5AVSZVDX2WPZ"
reporter = "lognd"
created = "2026-10-08T04:54:34Z"
updated = "2026-10-08T04:54:34Z"
scope = ["changelog.d/**", "crates/gob-symbols/**", "crates/gob-check/**"]

[[acceptance]]
text = "Given a strict-clean TS file, when resolved, then method dispatch on concrete types is Must and any-typed sites are dynamic"
bound = false
+++

docs/design/cohesion.md 2.2.
