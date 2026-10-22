+++
id = "01M5HDAS62G7H4YY9FVG59GJ01"
title = "Wire grimble-lints effect::scan into the registered PAIR001 rule for React effects"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T08:58:34Z"
updated = "2026-10-22T23:45:28Z"
scope = ["crates/grimble-lints/**", "changelog.d/**"]

[[acceptance]]
text = "Given a useEffect starting an interval without cleanup in a scanned file, when grimble check runs, then PAIR001 is reported through the registered rule"
bound = false
+++

Follow-up from ~7ASNXV3: effect::scan exists but is not yet called by the rule.
