+++
id = "01M4D95VS2KPK91REEZ8KA74BB"
title = "stylelint JSON parser and crunk id map for generic CSS hygiene (Advisory)"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-08T08:13:19Z"
updated = "2026-10-08T08:13:19Z"
scope = ["changelog.d/**", "crates/gob-check/**", "crates/crunk-check/**"]

[[acceptance]]
text = "Given stylelint --formatter json output, when crunk check runs the stage, then findings carry crunk ids and declaration-no-important is Advisory"
bound = false
+++

notes/research/lint-catalogue-2026-10-08.md row W06 (4.2 N09); notes/research/creators-web-2026-10-08.md WADV025 (6 voices), WADV031 (5); WADV051 !important is contested, so Advisory.
