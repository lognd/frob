+++
id = "01M3Z714TX00GDEADXET0GMFJA"
title = "G18: grimble migrate from v1 strata files"
type = "task"
category = "todo"
priority = "low"
points = 8
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:25Z"
updated = "2026-10-02T21:06:25Z"
idempotency_key = "m2-migrate"
labels = ["milestone:2"]
scope = ["crates/grimble-model/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z713VGKF4Z0JJ3263XJMC3"

[[links]]
kind = "blocked-by"
target = "01M3Z714EEST9EGEHWWV56RXG4"

[[acceptance]]
text = "Given the v1 frob repository's strata files, when migrated, then grimble check parses the output and lists unconverted constructs"
bound = false
+++

migration.md: convert design/*.strata to .grmb, map SYS ids many-to-one, carry excuses as exception kinds, report what could not be carried.
