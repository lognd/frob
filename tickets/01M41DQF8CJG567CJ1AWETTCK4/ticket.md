+++
id = "01M41DQF8CJG567CJ1AWETTCK4"
title = "PM001/PM002/PM034 skipped when the ledger holds milestones but no tickets"
type = "bug"
category = "in-progress"
priority = "low"
reporter = "lognd"
created = "2026-10-03T17:41:57Z"
updated = "2026-10-03T19:11:52Z"
scope = ["crates/frob-check/src/snapshot.rs", "crates/frob/tests/milestone.rs"]

[[acceptance]]
text = "Given a ledger with one milestone without exit criteria and no tickets, when frob check runs, then PM001 fires"
bound = true
+++

found while working ~3750GWB. open_ledger in crates/frob-check/src/snapshot.rs returns None when the ledger has zero tickets ("ledger holds no tickets: ledger rules are skipped"), so milestones (which are not tickets) are never counted and the repo:pm rules are not applicable. Repro: mkdir r && cd r && git init && git config user.email a@b.c && git config user.name n && frob init && git add -A && git commit -m b && frob milestone new 0.1.0 --goal g && frob check --json --fail-on none  -> no PM001 or PM002 finding (data.counts.warn is 0). Then `frob ticket new --title t` and re-run check -> PM001 and PM002 warnings appear. Expected: PM001 fires with the milestone alone.
