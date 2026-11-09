+++
id = "01M703GDA7AME8ZR6PJGM874K5"
title = "Grimble LOG: Java adapter must record call sites so U can witness LOG001"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-09T12:11:11Z"
updated = "2026-11-09T13:25:33Z"
scope = ["crates/gob-symbols/src/java*.rs", "crates/gob-symbols/src/pipeline.rs", "crates/grimble-check/src/log/universal.rs", "docs/design/grimble/output-atoms.md", "changelog.d", "crates/gob-symbols/src/fold.rs", "crates/gob-symbols/src/go.rs"]
+++

found while working ~MV8PWVD: extract_file yields no calls or uses for Java; universal.rs separator() cannot enable java until it does
