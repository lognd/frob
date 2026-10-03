+++
id = "01M41S1KC8PQFTVDETMARHP82G"
title = "gob-path crate: RelPath moved from gob-git, Shown, component validation, typed-path property tests"
type = "story"
category = "todo"
priority = "high"
points = 5
parent = "01M41S1JXXN380WPE29ATR5EP7"
reporter = "lognd"
created = "2026-10-03T20:59:43Z"
updated = "2026-10-03T20:59:43Z"
scope = ["crates/gob-path/**", "crates/gob-git/src/relpath.rs", "crates/gob-git/src/lib.rs", "crates/gob-git/Cargo.toml", "Cargo.toml", "docs/design/paths.md"]

[[acceptance]]
text = "Given random Windows-style and Unix-style host paths under a root, when from_host then to_host runs, then the original path is returned and the RelPath uses only /"
bound = false

[[acceptance]]
text = "Given a component that is invalid on any supported platform, when RelPath is built, then it is refused naming the component and the platform"
bound = false

[[acceptance]]
text = "Given gob-git callers, when they use RelPath, then they compile unchanged through the re-export"
bound = false
+++

paths.md sections 1 and 4. New leaf crate gob-path. RelPath moves here (gob-git re-exports it for one release). Bridges: RelPath::from_host(root, p) by components (strip_prefix, never string prefixes; refuse outside root; join with /; refuse components invalid on any supported platform: reserved device names, <>:"|?*, trailing dot or space, backslash), RelPath::to_host(root) by Path::join, Shown::of(p) for people (home as ~, the same scrub rule as ~33PZ67A's PathScrub: move or share it, one function). Logic is written over a path style with the typed-path crate and property-tested with Windows paths on Linux (drive letters, UNC, mixed separators, case, reserved names) and Unix paths.
