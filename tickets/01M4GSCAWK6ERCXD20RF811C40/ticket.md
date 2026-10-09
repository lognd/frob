+++
id = "01M4GSCAWK6ERCXD20RF811C40"
title = "Progress readout on interactive TTYs for slow verbs (check, land, test, ack, ticket doable): one self-overwriting status line with a spinner, phase name and counters, like ../cloc"
type = "story"
category = "todo"
priority = "low"
points = 3
reporter = "lognd"
created = "2026-10-09T16:53:54Z"
updated = "2026-10-09T16:53:54Z"
scope = ["crates/gob-cli/**", "crates/gob-check/**", "crates/frob-land/**", "changelog.d/**"]

[[acceptance]]
text = "Given an interactive TTY and a verb running longer than 250 ms, when it runs, then stderr shows one self-overwriting line (spinner, current phase such as walking/parsing/rules/tool:clippy/siblings/merge/close, counters and elapsed time) that disappears when the verb finishes"
bound = false

[[acceptance]]
text = "Given --json output, a non-TTY stderr, NO_COLOR/CI environments or --no-progress, when the verb runs, then no progress is drawn and output is byte-identical to today"
bound = false

[[acceptance]]
text = "Given log lines emitted during a run, when the readout is active, then a log line never shares a line with the readout (the readout is erased first and redrawn on the next tick)"
bound = false
+++

Owner 2026-10-09 (low priority). Reference design: ../cloc crates/clocx/src/progress.rs (lock-free phase and counters advanced by compute code, which never draws) and crates/clocx/src/render/progress.rs (drawer thread, 80 ms tick, nothing drawn before 250 ms so warm runs do not flicker, LogWriter erases the line before a log line). Put the shared readout in gob-cli so frob, grimble and crunk all get it; phases come from the existing --timing stage spans.
