+++
id = "01M6BNZWXFPCJDSEA0R2ZY6EDP"
title = "LOG001 false positive on subprocess.run capture_output when stdout is read"
type = "bug"
category = "in-progress"
priority = "low"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T13:50:10Z"
updated = "2026-11-01T16:01:27Z"
scope = ["crates/grimble-check/src/log/catalogue.rs", "crates/grimble-check/src/log/lang_python.rs", "crates/grimble-check/src/log/lang_rust.rs", "crates/grimble-check/src/log/lang_js.rs", "crates/grimble-check/src/log/lang_csharp.rs", "crates/grimble-check/tests/log_rules.rs", "docs/design/output-atoms.md", "docs/reference/rules/LOG001.md", "crates/grimble-check/src/rules/log001.md"]

[[acceptance]]
text = "LOG001 does not flag subprocess.run(..., capture_output=True) whose .stdout is read; test covers it"
bound = true
+++
