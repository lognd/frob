+++
id = "01M4H0WVC6FWGRT62ZP3NMT0GQ"
title = "Sibling document packs[] entries carry source provenance (repo:packs/NAME)"
type = "task"
category = "todo"
priority = "low"
points = 3
reporter = "lognd"
created = "2026-10-09T19:05:33Z"
updated = "2026-10-28T12:55:42Z"
labels = ["no-story"]
scope = ["crates/gob-check/src/sibling_doc.rs", "crates/gob-check/src/sibling.rs"]

[[links]]
kind = "blocked-by"
target = "01M4D8Y28W7XK0H2F3EWAZA1EH"

[[acceptance]]
text = "Given a repo pack loaded from packs/NAME.toml, when check --json runs, then packs[] carries source repo:packs/NAME"
bound = false
+++

found while working ~AMVHK82: PackRef has only name, version, digest, so a repo pack's provenance repo:packs/NAME is only logged.

no-story: internal engineering task in gob-check; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
