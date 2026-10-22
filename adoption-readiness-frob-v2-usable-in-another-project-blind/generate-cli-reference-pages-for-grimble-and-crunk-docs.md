+++
id = "01M4CXTR91E8Y8Y52B5ARDPKKS"
title = "Generate CLI reference pages for grimble and crunk (docs/reference/cli/grimble.md, crunk.md)"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M4CTTPJ00PTDE0A1SE4MJFCF"
reporter = "lognd"
created = "2026-10-08T04:55:01Z"
updated = "2026-10-22T08:20:07Z"
scope = ["changelog.d/**", "crates/gob-dev/**", "docs/reference/**"]

[[acceptance]]
text = "Given cargo dev gen, when run, then grimble.md and crunk.md exist and GEN001 keeps them current"
bound = true
+++

Follow-up from ~9X572Y1; documentation.md expects one page per product.
