+++
id = "01M5HBHRPS50C0M7RJRCFF3C0J"
title = "VIS001: register the rule in crunk-rules and wire render/PNG decode and diff encode"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T08:27:26Z"
updated = "2026-11-14T19:11:13Z"
labels = ["no-story"]
scope = ["crates/crunk-rules/**", "crates/crunk-gallery/**", "docs/reference/rules/**", "docs/crunk/rules/**", "Cargo.lock"]

[[acceptance]]
text = "crunk_gallery::png_io decodes PNG renders to RGBA8 and encodes the VIS001 diff image as PNG, round-tripping pixels exactly."
bound = true

[[acceptance]]
text = "GAP: the VIS001 #[rule] in crunk-rules, its md page, and the [vis] crunk.toml thresholds are NOT done: id VIS001 is already grimble-arch's arch-wide-visibility rule (family VIS owned by grimble-arch), so a crunk rule needs a new id first."
bound = false
+++

Found while doing ~R149H7C: the pure comparison (crunk_gallery::visual) exists. Still needed: a VIS001 #[rule] declaration plus md in crunk-rules, [vis] thresholds in crunk.toml, PNG decode of design and build renders and PNG encode of the diff image at the diff path (needs a png dependency and the T2 renderer).

no-story: internal engineering task in crunk-rules; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
