+++
id = "01M6BNZX0P141Y74ECBHNDEJ62"
title = "LOG001 scanner misses stored-handle is_terminal (is_tty on std::io::stdout())"
type = "bug"
category = "in-progress"
priority = "low"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T13:50:10Z"
updated = "2026-11-01T16:18:30Z"
scope = ["crates/grimble-check/src/log/lang_rust.rs"]

[[acceptance]]
text = "Stored handles passed to is_tty/is_terminal are classified correctly; test in gob-cli case"
bound = false
+++
