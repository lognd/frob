+++
id = "01M43ATE06MNRNVJJ314KW24RJ"
title = "crunk-gallery: triage server, verbs and gallery check"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:29:37Z"
updated = "2026-10-21T12:22:12Z"
idempotency_key = "crunk-plan-gal3"
labels = ["area:crunk"]
scope = ["crates/crunk-gallery/src/triage/**", "crates/crunk/src/gallery.rs", "crates/crunk-gallery/tests/triage*.rs", "crates/crunk-gallery/src/lib.rs", "crates/crunk/src/lib.rs", "crates/crunk/tests/gallery.rs", "crates/crunk-gallery/README.md", "docs/crunk/gallery.md", "docs/crunk/README.md", "changelog.d/01M43ATE06MNRNVJJ314KW24RJ.added.md", "crates/crunk-gallery/Cargo.toml", "Cargo.lock", "crates/crunk/Cargo.toml", "design/model.grmb"]

[[links]]
kind = "blocked-by"
target = "01M43ATDR7DWY5RZPB3QB3GE3K"

[[acceptance]]
text = "Given rendered cells, when `crunk gallery triage` runs, then a local contact sheet serves and verdicts are saved to the manifest"
bound = true

[[acceptance]]
text = "Given an expired approval, when `gallery check --json` runs, then GALLERY003 is reported and validates against gallery-check.v1"
bound = true

[[acceptance]]
text = "Given the crate dependency list, when the repo dependency rule runs, then crunk-gallery does not depend on tokio directly"
bound = true
+++

Port triage (local HTTP contact sheet, keyboard verdicts) and the `gallery enumerate|render|triage|check` verbs. The HTTP server needs tokio, which boundaries.md 6 confines to gob-serve and the serve crates: depend on gob-serve (or record the exception in an owner decision) rather than adding tokio to crunk-gallery. Port tests/unit/test_gallery_triage.py and _render.py.
