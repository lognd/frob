+++
id = "01M4GR6HMS7VPTVZ9C23AP1RKR"
title = "Raise [pm.wip] in_progress from 10 to 16: owner wants wider parallel waves; tests run on goway helpers, not local builds"
type = "chore"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-09T16:33:33Z"
updated = "2026-10-09T16:34:34Z"
scope = ["frob.toml", "changelog.d/**"]

[[acceptance]]
text = "Given frob.toml, when the change lands, then [pm.wip] in_progress is 16 with a comment stating why"
bound = true
+++

Owner 2026-10-09: use as many agents as needed while watching resources; goway per-host fitting (~K60F05J) now spreads suite runs over both helpers.
