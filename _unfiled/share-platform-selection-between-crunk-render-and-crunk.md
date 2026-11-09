+++
id = "01M6YTV82ECZNYWGGVMZS38FNS"
title = "Share platform selection between crunk render and crunk-gallery cells"
type = "chore"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-09T00:20:35Z"
updated = "2026-11-09T04:08:07Z"
scope = ["crates/crunk-spec/src/model.rs", "crates/crunk-gallery/src/cells.rs", "crates/crunk/src/render.rs", "crates/crunk-spec/tests/spec.rs"]
+++

found while working ~FHHY9Z7: crunk render replicates crunk-gallery cell enumeration because the gallery crate is optional; move platform/cell selection into crunk-spec and call it from both.
