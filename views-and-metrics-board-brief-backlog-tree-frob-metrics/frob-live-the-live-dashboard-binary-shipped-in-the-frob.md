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
updated = "2026-11-12T03:50:59Z"
labels = ["no-story"]
scope = ["crates/frob-live/**", "crates/frob/**", "packaging/**", ".github/workflows/release.yml", "Cargo.lock", ".github/workflows/build-smoke.yml", ".github/workflows/ci.yml", "crates/frob-release/tests/it/products.rs", "crates/gob-dev/src/wheel.rs", "dist-workspace.toml", "docs/MOVED.toml", "docs/README.md", "docs/assets", "docs/decisions", "docs/design", "docs/grimble", "docs/guides", "docs/history", "docs/migration", "docs/packs", "docs/reference", "docs/schemas", "changelog.d/01KZ7KGKHYQ1QZ0BHKB49P22KK.changed.md", "changelog.d/01M1QDTYR2FFF5HYHVZP2W1WMP.fixed.md", "changelog.d/01M1QDTYRJ3P3GT8828GCNECVB.added.md", "changelog.d/01M1T07NW78MGWRF7HZQMPSRAV.security.md", "changelog.d/01M1T07NWAFVRT2V4RAPVJ9SQM.added.md"]

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
