+++
id = "01M6D6ZVHS9H1M7EKM8DTPYD6V"
title = "grimble-model keywords test reads stale spec path docs/design/grmb-spec.md"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-02T04:06:29Z"
updated = "2026-11-02T04:23:08Z"
scope = ["crates/grimble-model/tests/keywords.rs"]

[[acceptance]]
text = "The keywords test reads docs/design/grimble/grmb-spec.md and all keywords tests pass"
bound = true
+++

found while working ~0Q2TMVM: tests/keywords.rs spec() joins ../../docs/design/grmb-spec.md but the spec lives at docs/design/grimble/grmb-spec.md; 3 tests fail.
