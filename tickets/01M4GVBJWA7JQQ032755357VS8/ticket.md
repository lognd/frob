+++
id = "01M4GVBJWA7JQQ032755357VS8"
title = "experimental CI red: CAP001 fires on frob-v2's own model since ~FSW5067 (no may grants for fs.read and exec in design/model.grmb)"
type = "bug"
category = "todo"
priority = "critical"
points = 2
reporter = "lognd"
created = "2026-10-09T17:28:44Z"
updated = "2026-10-09T17:28:44Z"
scope = ["design/**", "changelog.d/**"]

[[acceptance]]
text = "Given frob-v2's design/model.grmb, when frob check runs on experimental, then no CAP001 Error fires: each node declares the capabilities it really uses (fs.read where code reads files; exec only at test selectors and the process-spawning crates gob-exec and gob-git), scoped with at selectors, and grimble check is clean"
bound = false
+++

CI run 37963150506 at ec63b582: 6 CAP001 errors (node/frob, node/gob, node/grimble, node/crunk; fs.read and exec). Culprit land: ~FSW5067 (CAP001 now fires; its land check was ticket-scoped).
