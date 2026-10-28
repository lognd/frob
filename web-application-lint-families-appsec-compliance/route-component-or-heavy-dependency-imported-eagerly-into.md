+++
id = "01M4D95SJZKFVHSZHKAZ80TDP9"
title = "Route component or heavy dependency imported eagerly into the entry bundle (Advisory)"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M2Y1SS0MVHB8M891RN134SE7"
reporter = "lognd"
created = "2026-10-08T08:13:17Z"
updated = "2026-10-28T12:56:07Z"
labels = ["no-story"]
scope = ["changelog.d/**", "crates/grimble-websec/**", "crates/gob-frameworks/**"]

[[acceptance]]
text = "Given a react-router route whose component is imported statically from the entry module, when checked, then the finding names the route"
bound = false

[[acceptance]]
text = "Given lazy(() => import(...)) for the route, when checked, then clean"
bound = false
+++

notes/research/lint-catalogue-2026-10-08.md row W04 (4.2 N22); notes/research/creators-web-2026-10-08.md WADV006 (7 voices incl. Web Almanac data) and 5.2 item 2 (no linter does route-aware checks).

no-story: internal engineering task in grimble-websec; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
