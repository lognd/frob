+++
id = "01M7EXT3X9DSSHYJWNQ4ZQPV00"
title = "frob tool verb: list, suggest, add, doctor over std-pack tool definitions with [meta] detect/category/languages"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:20:14Z"
updated = "2026-11-15T06:20:14Z"
idempotency_key = "static-research-k4"
labels = ["no-story"]
+++

Source: /home/logan/projects/frob-research-static-analysis.md section 6 item 4, section 4.3 steps 1 and 4. Rationale: tool definitions in crates/gob-check/src/tools/*.toml (12 today: actionlint, api-extractor, cargo-semver-checks, clang-format, dotnet-format, gofmt, griffe, prettier, ruff-format, ruff, rustfmt, zizmor) are a registry in embryo with no verb. Remedy: additive [meta] table (languages, detect globs, category, homepage, license, install recipes) in tool_def.rs; new verb frob tool list (registry plus installed state), suggest (detected stack -> unconfigured tools), add <name> (writes the [[check.tool]] stanza with pinned version), doctor (version range mismatch, missing binary). Reuse the existing tool registry/UNMEASURED machinery (T-ticket 5W6AQ0H done) instead of a second one. Crates/files: crates/gob-check/src/tool_def.rs, tools/*.toml, crates/frob (new verb).
