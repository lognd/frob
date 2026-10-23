+++
id = "01M5HJ075VJZAP88EVTCX1MH8C"
title = "Wire COH002 into a registered rule and the [coh] config"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T10:20:11Z"
updated = "2026-10-23T00:08:40Z"
scope = ["crates/grimble-check/**", "docs/**"]

[[acceptance]]
text = "Given a [coh] config table with custom effect and trivial vocabularies, when grimble check runs on a file with a mixed-concern unit, then COH002 is reported through a registered rule using those vocabularies"
bound = true

[[acceptance]]
text = "Given no [coh] table, when grimble check runs, then COH002 uses the built-in default vocabularies"
bound = true
+++

COH002 is a detector library only; effect and trivial vocabularies are hardcoded defaults. Declare the rule and expose the vocabularies in config.
