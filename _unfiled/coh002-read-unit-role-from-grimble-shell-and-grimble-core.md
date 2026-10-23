+++
id = "01M5HJ078MGFERVXX3DSJT111F"
title = "COH002: read unit role from grimble:shell and grimble:core directives"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T10:20:11Z"
updated = "2026-10-23T02:23:33Z"
scope = ["crates/grimble-check/**", "docs/**"]

[[acceptance]]
text = "Given a unit carrying a grimble:shell or grimble:core directive, when COH002 runs, then the role is read from the directive without the caller supplying it"
bound = false

[[acceptance]]
text = "Given a unit with no role directive, when COH002 runs, then the caller-supplied role (or none) is used unchanged"
bound = false
+++

The caller supplies the role today; extract it from directives.
