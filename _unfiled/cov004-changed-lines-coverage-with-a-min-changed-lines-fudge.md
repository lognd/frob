+++
id = "01M7EXV8YEQZF73MP3NJHVKZ9W"
title = "COV004 changed-lines coverage with a min_changed_lines fudge factor"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:20:52Z"
updated = "2026-11-15T06:20:52Z"
idempotency_key = "static-research-k10"
labels = ["no-story"]
+++

Source: /home/logan/projects/frob-research-static-analysis.md section 6 item 9, sections 1.3 and 1.9. Rationale: Sonar ignores percentage conditions on tiny diffs (fewer than 20 new lines) and diff-cover judges only changed lines. Report says whether COV004 has a minimum-lines guard is not verified: CoverageThreshold in crates/frob-evidence/src/config.rs shows scope and line fields and no min_changed_lines at HEAD, so verify first. Remedy: compute coverage over lines changed vs base (the ratchet's base tip) and add optional min_changed_lines, below which the percentage condition is skipped with an info note. Crates/files: crates/frob-evidence/src/config.rs, coverage module, crates/frob-obligations/src/rules (COV004).
