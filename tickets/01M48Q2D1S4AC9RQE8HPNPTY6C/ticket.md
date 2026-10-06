+++
id = "01M48Q2D1S4AC9RQE8HPNPTY6C"
title = "frob-live: the live dashboard binary, shipped in the frob wheel, reached by board --live and stats --live"
type = "story"
category = "todo"
priority = "medium"
parent = "01M48Q294B33TB7C0GSATZRGJB"
reporter = "lognd"
created = "2026-10-06T13:39:53Z"
updated = "2026-10-06T13:39:53Z"
scope = ["crates/frob-live/**", "crates/frob/**", "packaging/**", ".github/workflows/release.yml", "Cargo.lock"]

[[links]]
kind = "blocked-by"
target = "01M48Q2AQXY69YKK3D2DC05ZWR"

[[acceptance]]
text = "board --live and stats --live start frob-live and q quits"
bound = false

[[acceptance]]
text = "frob's dependency tree has no ratatui or notify"
bound = false

[[acceptance]]
text = "the wheel and archives contain frob-live and the smoke test runs it with --help"
bound = false
+++

New crate crates/frob-live (ratatui, notify): redraws the frob-pm Board and frob-metrics stats values, refreshing on ledger, worktree and file changes (debounced) and on a timer for time windows, like clocx --live. frob execs the sibling binary found next to itself (sibling discovery, D87) for --live; frob links no TUI. The wheel and release archives ship frob-live beside frob, grimble and crunk.
