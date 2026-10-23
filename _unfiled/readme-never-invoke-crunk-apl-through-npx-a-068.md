+++
id = "01M1T07J3X8465F5CWXVVA5A3R"
title = "README: never invoke crunk/apl through npx (A-068)"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-09-06T00:00:03Z"
aliases = ["crunk:T-0125"]
labels = ["component:crunk", "source:crunk"]
scope = ["README.md"]

[[acceptance]]
text = "given the README, when read, then it states both binaries and warns against npx by name"
bound = true
+++

The adopting project's agents twice reached for npx (A-057 GraphQL CLI, A-068 an unrelated apl package) because the tool lints frontend repos where npx is muscle memory. Document plainly: crunk installs as a uv tool, both binaries live on PATH, npx must never be used and resolves unrelated npm packages.
