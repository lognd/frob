+++
id = "01M4FF53WPQXGCKTNYDN404RWV"
title = "Remove the .strata migration path from the design: grimble is not strata's successor (owner 2026-10-09); strata is deprecated"
type = "docs"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-09T04:36:15Z"
updated = "2026-10-10T19:06:32Z"
labels = ["grimble"]
scope = ["docs/design/**", "changelog.d/**"]

[[acceptance]]
text = "Given docs/design, when the change lands, then migration.md has no grimble migrate row for .strata, grimble-model.md no longer calls itself the v1 strata successor, the grimble verb list has no migrate, and README.md records the decision"
bound = true

[[acceptance]]
text = "Given migration.md, when the change lands, then it states that .strata models are rewritten by hand as .grmb (no tool)"
bound = true
+++

Owner decision 2026-10-09; dropped ~X85A7ZD.
