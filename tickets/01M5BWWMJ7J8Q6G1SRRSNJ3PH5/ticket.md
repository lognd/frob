+++
id = "01M5BWWMJ7J8Q6G1SRRSNJ3PH5"
title = "grimble check and exceptions list exceed profile budget (8s vs 3s)"
type = "bug"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-10-20T05:35:01Z"
updated = "2026-10-20T05:35:01Z"

[[acceptance]]
text = "grimble check and grimble exceptions list stay within the profile.toml budgets in cargo dev profile"
bound = false
+++

CI profile job (run 39373786096): grimble check warm median 8139 ms vs budget 5800 ms and cold 8088 ms vs 8000 ms; grimble exceptions list warm median 8059 ms vs 6200 ms. Both sit near 8s, so likely a shared slow path (config load or tree scan). Blocks the profile job and the 0.533.0 grimble-leaves-preview goal.
