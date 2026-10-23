+++
id = "01M5KDWHPF5YTVP64PYCXX0FRT"
title = "Wire grimble-ci into the grimble check pipeline so it can own the CI family"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-23T03:46:45Z"
updated = "2026-10-23T05:10:55Z"
scope = ["crates/grimble-check/**", "crates/grimble-ci/**"]

[[acceptance]]
text = "grimble check calls grimble_ci::analyze on workflow files and reports its findings"
bound = false

[[acceptance]]
text = "a zizmor finding and a grimble-ci finding for the same workflow and rule are reported once"
bound = false
+++

Found while working ~TXCDEKR. grimble-ci is not a dependency of any crate: nothing calls grimble_ci::analyze, so grimble check never reports CI003 and the gob-check declarations (crates/gob-check/src/rules.rs, Ci001/Ci003/Ci006/Ci007/Ci010/Ci014) plus the zizmor id map in tool_parse.rs are the only live owners. Wire grimble-ci in (and decide how a bound zizmor finding and the lexical grimble-ci finding for the same workflow dedupe), then ~TXCDEKR can retire the gob-check CI003 declaration and its docs note.
