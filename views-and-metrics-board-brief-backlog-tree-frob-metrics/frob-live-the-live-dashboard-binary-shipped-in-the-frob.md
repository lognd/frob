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
updated = "2026-11-12T03:51:05Z"
labels = ["no-story"]
scope = ["crates/frob-live/**", "crates/frob/**", "packaging/**", ".github/workflows/release.yml", "Cargo.lock", ".github/workflows/build-smoke.yml", ".github/workflows/ci.yml", "crates/frob-release/tests/it/products.rs", "crates/gob-dev/src/wheel.rs", "dist-workspace.toml", "docs/MOVED.toml", "docs/README.md", "docs/assets", "docs/decisions", "docs/design", "docs/grimble", "docs/guides", "docs/history", "docs/migration", "docs/packs", "docs/reference", "docs/schemas", "changelog.d/01KZ7KGKHYQ1QZ0BHKB49P22KK.changed.md", "changelog.d/01M1QDTYR2FFF5HYHVZP2W1WMP.fixed.md", "changelog.d/01M1QDTYRJ3P3GT8828GCNECVB.added.md", "changelog.d/01M1T07NW78MGWRF7HZQMPSRAV.security.md", "changelog.d/01M1T07NWAFVRT2V4RAPVJ9SQM.added.md", "changelog.d/01M1T07NX1SZYZBZYYW821FN00.added.md", "changelog.d/01M1T07NY615PQ6RAEB4CESXMT.security.md", "changelog.d/01M2VFD1ZAS7PZERWYPQDMB8GH.added.md", "changelog.d/01M2VFD1ZBJP6X2ACJ4KCF29W6.added.md", "changelog.d/01M2VFD1ZDWWNTW1FFGKHCKTS3.added.md", "changelog.d/01M3AXSDBMG2ZAEHTQ6JHA8CYK.fixed.md", "changelog.d/01M3DG64C705481E6V5X4W9S9S.fixed.md", "changelog.d/01M3DG64CFWRYVDS3DGW91G8EK.added.md", "changelog.d/01M3DG64CNAZ8K50HQ046VKHER.added.md", "changelog.d/01M3DG64ECQN5RFA286F6YXYRZ.added.md", "changelog.d/01M3Z713C4RW0T6XK1ZB7VH1B4.changed.md", "changelog.d/01M3Z7141TW2H3HXJRK1QBHP7T.added.md", "changelog.d/01M3Z714EEST9EGEHWWV56RXG4.added.md", "changelog.d/01M3Z714HJ6E02VGXH271BAAE0.added.md", "changelog.d/01M3Z714MQBXMW4PJVRQNDWNDM.added.md", "changelog.d/01M3Z714QT3QXEAJAK9JDDEB70.changed.md", "changelog.d/01M3Z714XYJEHXHNWXKVXAYFQJ.changed.md", "changelog.d/01M3Z7151078ZAM6AM1GFWC6QP.added.md", "changelog.d/01M3Z71542Y6NZG3G8A83EFRF2.added.md"]

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
