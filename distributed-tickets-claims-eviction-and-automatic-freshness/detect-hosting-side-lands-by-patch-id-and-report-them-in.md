+++
id = "01M5DT8FKY9HJW3R9Q4CZB283M"
title = "Detect hosting-side lands by patch id and report them in refresh output"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T23:27:32Z"
updated = "2026-10-21T00:26:10Z"
scope = ["crates/frob-land/src/hostland.rs"]
+++

Follow-up of DT22: match squash/rebase merges that lack a Frob-Ticket trailer by patch id, and surface recorded host lands in the refresh report/notices (currently logged only).
