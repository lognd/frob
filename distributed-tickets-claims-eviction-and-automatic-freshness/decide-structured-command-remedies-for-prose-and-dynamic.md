+++
id = "01M5DR9V9Z1MSTE5PP0ZM895NQ"
title = "Decide structured-command remedies for prose and dynamic with_remedy sites in crunk, grimble, gob-product"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T22:53:20Z"
updated = "2026-10-28T12:56:07Z"
labels = ["no-story"]
scope = ["crates/crunk/**,crates/grimble/**,crates/gob-product/**"]
+++

Found while working ~D00MKHS. Remaining with_remedy sites are prose ('fix crunk.toml as described, then rerun') or carry placeholders/dynamic text: crunk rule/tokens/diff/query/review/preview/fix/init, gallery manifest hints, grimble ack.rs (git switch <branch>, bind identity), grimble config_for.rs, gob-product workspace.rs (format!ed product name). Migrate those that can name a real command (e.g. ack detached head -> git switch <branch> as RemedyCommand) and leave the rest as text.

no-story: internal engineering task in crunk; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
