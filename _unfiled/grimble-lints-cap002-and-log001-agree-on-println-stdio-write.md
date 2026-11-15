+++
id = "01M7EXVJERZK52JPWZKSH4B3PP"
title = "grimble-lints: CAP002 and LOG001 agree on println! (stdio.write detector in built-in registry)"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:21:02Z"
updated = "2026-11-15T06:21:02Z"
labels = ["no-story"]

[[acceptance]]
text = "println! is detected as stdio.write with no pack enabled"
bound = false

[[acceptance]]
text = "A partial-detector atom yields Unresolved instead of a denial"
bound = false
+++

Audit: ~/projects/frob-audit2-grimble.md M10. Evidence: CAP002 denies a use that LOG001 reports on the same line; println! is a stdio.write detector only in packs/core-effects/atoms.toml:351 while [packs] enabled = []; std::env::args is not env.read. Remedy: detect print macros in the built-in registry, or CAP002 reports Unresolved for atoms whose detectors are partial. Crates: grimble-capabilities, grimble-check.
