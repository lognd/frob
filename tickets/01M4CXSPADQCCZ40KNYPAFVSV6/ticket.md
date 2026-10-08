+++
id = "01M4CXSPADQCCZ40KNYPAFVSV6"
title = "def_use capability: intra-unit def-use edges with Must/May strength (F2) and may-alias sources"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M4CXSN7VTEYX5AVSZVDX2WPZ"
reporter = "lognd"
created = "2026-10-08T04:54:26Z"
updated = "2026-10-08T04:54:26Z"
scope = ["changelog.d/**", "crates/gob-ir/**", "crates/gob-symbols/**"]

[[acceptance]]
text = "Given fixtures in Rust, Python and TypeScript, when def_use runs, then Must and May edges match golden files, with self attributes, setattr, kwargs and by-reference closures as May"
bound = false
+++

docs/design/cohesion.md 1.1 and 3.
