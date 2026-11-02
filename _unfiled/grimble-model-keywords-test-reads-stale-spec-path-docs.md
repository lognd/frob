+++
id = "01M6D6ZVHS9H1M7EKM8DTPYD6V"
title = "grimble-model keywords test reads stale spec path docs/design/grmb-spec.md"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-02T04:06:29Z"
updated = "2026-11-02T04:06:29Z"
scope = ["crates/grimble-model/tests/keywords.rs"]
+++

found while working ~0Q2TMVM: tests/keywords.rs spec() joins ../../docs/design/grmb-spec.md but the spec lives at docs/design/grimble/grmb-spec.md; 3 tests fail.
