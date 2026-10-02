+++
id = "01M3Z714HJ6E02VGXH271BAAE0"
title = "G15: grimble shrink"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:25Z"
updated = "2026-10-02T21:06:25Z"
idempotency_key = "m2-shrink"
labels = ["milestone:2"]
scope = ["crates/grimble-bind/**", "crates/grimble-capabilities/**", "crates/grimble-model/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z713VGKF4Z0JJ3263XJMC3"

[[links]]
kind = "blocked-by"
target = "01M3Z714EEST9EGEHWWV56RXG4"

[[acceptance]]
text = "Given a model with a grant no detector observes, when grimble shrink runs, then the diff proposes removing it and nothing is written without --apply"
bound = false
+++

Shrink a model to what the code still supports: remove declared-unused grants with an excuse prompt, propose owns selectors from ownership, print a diff; dry-run by default.
