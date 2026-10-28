+++
id = "01M4KHD7774ZV3YECPVCGE2RGD"
title = "Read dotfile templates (.env.example) as key=value text instead of opaque"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "Claude"
created = "2026-10-10T18:32:35Z"
updated = "2026-10-28T12:55:50Z"
labels = ["no-story"]
scope = ["crates/gob-languages/**", "crates/gob-symbols/**", "crates/frob-check/**"]

[[acceptance]]
text = "Given a .env.example file with KEY=value lines and # comments, when frob check classifies files, then it is read as text by a key=value reader and is not counted as an opaque text file"
bound = false
+++

Split from ~T54E67N (logand F-556): no key=value reader exists, so classifying dotfile templates needs a new language/adapter in gob-languages and gob-symbols, outside the T54E67N scope.

no-story: internal engineering task in gob-languages; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
