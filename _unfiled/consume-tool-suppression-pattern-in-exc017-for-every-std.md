+++
id = "01M7EXT29F1DJWDA1TM6F9TWTE"
title = "Consume tool suppression_pattern in EXC017 for every std-pack tool recipe"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:12Z"
updated = "2026-11-15T06:20:13Z"
idempotency_key = "static-research-k3"
labels = ["no-story"]

[[acceptance]]
text = "EXC017 flags a native suppression comment matching a bound tool's suppression_pattern, covered by a mdtest case"
bound = false

[[acceptance]]
text = "Every std-pack tool recipe with an inline suppression syntax declares suppression_pattern, or states in a comment that it has none"
bound = false
+++

Source: ~/projects/frob-research-static-analysis.md section 6 item 3, section 4.3 step 7. Rationale: suppression_pattern is declared in crates/gob-check/src/tool_def.rs and only set in tools/ruff.toml and tools/zizmor.toml; the report claims it is recorded but not consumed. Verify first: EXC017 lives in crates/frob-obligations/src/native.rs and grep shows no reference to suppression_pattern there, but confirm how native suppressions are detected before changing. Remedy: make EXC017 read the pattern from the bound tool definition, and add a pattern to every std-pack recipe whose tool has an inline suppression comment (eslint-disable, nolint, nosemgrep, shellcheck disable, etc). Crates/files: crates/frob-obligations/src/native.rs, crates/gob-check/src/tool_def.rs, crates/gob-check/src/tools/*.toml.
