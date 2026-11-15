+++
id = "01M7EXW5ZR1WVZ34SXKG0ADCGG"
title = "grimble-capabilities: database atom so sqlite3 does not raise CAP002 on fs.*"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:21:22Z"
updated = "2026-11-15T06:21:22Z"
labels = ["no-story"]

[[acceptance]]
text = "sqlite3.connect maps to a database atom"
bound = false

[[acceptance]]
text = "No fs.* CAP002 for it"
bound = false
+++

Audit: ~/projects/frob-audit2-grimble.md friction log. sqlite3 triggers CAP002 on fs.* because no database atom exists. Files: packs/core-effects/atoms.toml and detectors.
