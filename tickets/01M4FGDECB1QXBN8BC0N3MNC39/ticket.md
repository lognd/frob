+++
id = "01M4FGDECB1QXBN8BC0N3MNC39"
title = "docs/design/README.md parses partially (DOC001, 1 hole) on experimental"
type = "docs"
category = "todo"
priority = "low"
points = 1
reporter = "lognd"
created = "2026-10-09T04:58:08Z"
updated = "2026-10-09T04:58:08Z"
labels = ["docs"]
scope = ["docs/design/README.md", "changelog.d/**"]

[[acceptance]]
text = "Given docs/design/README.md, when frob check --only DOC runs, then no DOC001 is reported for it"
bound = false
+++

Found while working ~83H49E3: frob check --only DOC reports DOC001 (file parsed partially, 1 hole) on docs/design/README.md as it is on experimental before the D124-D133 rows; subjects inside the hole cannot be decided. Locate the construct the markdown adapter cannot parse and fix it.
