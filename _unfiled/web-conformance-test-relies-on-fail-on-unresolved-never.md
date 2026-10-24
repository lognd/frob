+++
id = "01M5P15BEM7AK8EW4Q7VM50AGH"
title = "web_conformance test relies on fail_on_unresolved=never because DEAD001 has no entry points"
type = "chore"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-24T04:02:05Z"
updated = "2026-10-24T04:02:05Z"
scope = ["crates/frob/tests/siblings/**"]
+++

found while working ~MJZYWH9: the grimble check web fixture has zero DEAD001 subjects (must_measure), so the default gate fails; give the fixture an entry point and drop the override.
