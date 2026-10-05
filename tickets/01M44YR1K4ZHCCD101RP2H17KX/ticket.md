+++
id = "01M44YR1K4ZHCCD101RP2H17KX"
title = "Migrate project-hullbreach platform from frob v1 to v2 (post-0.532.0 trial)"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-05T02:37:05Z"
updated = "2026-10-05T02:40:44Z"
idempotency_key = "d94-migplat"
scope = ["docs/migration/**", "notes/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z714TX00GDEADXET0GMFJA"

[[links]]
kind = "blocked-by"
target = "01M44YYNMG7X03Z76JY8PFY636"

[[links]]
kind = "blocked-by"
target = "01M44YYP1SH9VVNAY5A62XMCHN"

[[acceptance]]
text = "Given a scratch clone of platform, when frob migrate runs with --dry-run, then the counts per ticket disposition, unmapped config keys and waiver ids are listed with no file written"
bound = false

[[acceptance]]
text = "Given the migrated clone, when frob check runs under v2, then the findings differ from the v1 run only by explained entries recorded in the report"
bound = false

[[acceptance]]
text = "Given any v2 gap found, when the trial ends, then a ticket exists for it and is linked to this one"
bound = false
+++

Trial migration of the platform repository (Python with some TS/TSX and CSS, a crunk.toml, 130 v1 tickets, a hullbreach.strata design file, a frob.toml with three [[test.runner]] tables and many [[refs.entrypoint]] tables, no frob.lock) using the verbs of docs/design/migration.md (frob migrate tickets, config, directives, exceptions; grimble migrate for design/*.strata), run in a scratch clone first with --dry-run, then merged into the repository by its owner; frob2 runs side by side with v1 and `frob2 compare --against frob` until the diff is explained (migration.md section 2); only acks current under v1 carry over. The ticket does not modify the hullbreach repository from this checkout: the work happens in a scratch clone, and any change to the real repository is a reviewed change the owner lands. Python is covered by the first-party adapter and the pytest provider (~HKNM4VV, done); TS/TSX and CSS stay opaque until ~17ZVW3R lands, with the Unresolved count recorded as the baseline. Output: a findings diff report, a list of unmapped v1 config keys and rule ids, and tickets for each v2 gap found. Needs the migration tooling and the grimble strata migration (~T0GMFJA).
