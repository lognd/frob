+++
id = "01M48Q2D1S4AC9RQE8HPNPTY6C"
title = "frob-live: the live dashboard binary, shipped in the frob wheel, reached by board --live and stats --live"
type = "task"
category = "in-progress"
priority = "medium"
points = 8
parent = "01M48Q294B33TB7C0GSATZRGJB"
reporter = "lognd"
created = "2026-10-06T13:39:53Z"
updated = "2026-11-12T03:53:03Z"
labels = ["no-story"]
scope = ["crates/frob-live/**", "crates/frob/**", "packaging/**", ".github/workflows/release.yml", "Cargo.lock", ".github/workflows/build-smoke.yml", ".github/workflows/ci.yml", "crates/frob-release/tests/it/products.rs", "crates/gob-dev/src/wheel.rs", "dist-workspace.toml", "docs/**", "changelog.d/01M48Q2D1S4AC9RQE8HPNPTY6C.*", "crates/gob-dev/src/wheel_smoke.rs", "changelog.d/01M5XNNHN8RQ6486GS073YMCSS.security.md", "changelog.d/01M5XNNHRFE1K2DHBD7S9HQ7A6.security.md", "changelog.d/01M5XNNHV9M8HCP76TD867GGVJ.changed.md", "changelog.d/01M5XNNHY7KZDKBZKK2MM08TTF.fixed.md", "changelog.d/01M5XNNJ994RN6Y24AT6ZD117V.security.md"]

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

no-story: internal engineering task in frob-live; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
