+++
id = "01M41S1SMY1V34MP6Y4YGK8FGN"
title = "Persisted types hold RelPath only: ledger, locks, findings JSON, config"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M41S1JXXN380WPE29ATR5EP7"
reporter = "lognd"
created = "2026-10-03T20:59:50Z"
updated = "2026-10-03T20:59:50Z"
scope = ["crates/frob-ledger/**", "crates/gob-lock/**", "crates/gob-diagnostics/**", "crates/gob-config/**"]

[[links]]
kind = "blocked-by"
target = "01M41S1KC8PQFTVDETMARHP82G"

[[acceptance]]
text = "Given the persisted model types, when the audit test runs, then none holds PathBuf or an unvalidated path string"
bound = false
+++

paths.md section 1 and step 4. Audit every serialized type for PathBuf or a path in a String; convert to RelPath (or LocalPath for local-only data under .git/, never committed). Add a test that walks the serde-derived persisted types (or a disallowed-types clippy entry scoped to their modules) so a PathBuf cannot be added back.
