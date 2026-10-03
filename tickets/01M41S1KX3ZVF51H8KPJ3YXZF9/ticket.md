+++
id = "01M41S1KX3ZVF51H8KPJ3YXZF9"
title = "Clippy confinement: path-to-text conversion only in gob-path, with a shrinking allow list"
type = "story"
category = "todo"
priority = "high"
points = 3
parent = "01M41S1JXXN380WPE29ATR5EP7"
reporter = "lognd"
created = "2026-10-03T20:59:44Z"
updated = "2026-10-03T20:59:44Z"
scope = ["clippy.toml", "Cargo.toml", "crates/gob-path/**", "docs/design/paths.md"]

[[links]]
kind = "blocked-by"
target = "01M41S1KC8PQFTVDETMARHP82G"

[[acceptance]]
text = "Given a new path-to-text call outside gob-path in a crate not on the allow list, when cargo clippy -D warnings runs, then it fails naming the method and the gob-path replacement"
bound = false

[[acceptance]]
text = "Given a crate on the allow list with no remaining conversions, when the list test runs, then it fails asking to remove the entry"
bound = false
+++

paths.md section 3. Workspace clippy.toml disallowed-methods for Path::to_str, to_string_lossy, display, OsStr::to_str, to_string_lossy and their owned forms; disallowed-types for PathBuf in persisted-type modules. gob-path is allowed with #[expect(..., reason)] per site. Every other crate that still converts gets a crate-level #[expect] listed in one place (a checked list in paths.md or a test) so the list can only shrink; a test fails if a crate not on the list converts or a listed crate no longer needs its entry.
