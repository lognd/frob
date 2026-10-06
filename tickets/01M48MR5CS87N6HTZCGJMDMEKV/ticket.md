+++
id = "01M48MR5CS87N6HTZCGJMDMEKV"
title = "Generated artifacts: one cargo dev gen kind per artifact with --mode check/write/dry-run and a list of every generated file (ruff generate-all)"
type = "task"
category = "todo"
priority = "low"
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T12:59:21Z"
updated = "2026-10-06T12:59:21Z"
scope = ["crates/gob-dev/**", "crates/gob-symbols/src/languages_page.rs", "docs/reference/**"]

[[acceptance]]
text = "docs/reference/languages.md is produced by cargo dev gen and checked by GEN001"
bound = false

[[acceptance]]
text = "cargo dev gen --dry-run prints a capped diff and writes nothing"
bound = false

[[acceptance]]
text = "a generated-files manifest lists every generated path and GEN001 fails on an unlisted generated file"
bound = false
+++

Macro and codegen review 2026-10-06: our gen with --check and GEN001 matches ruff's cargo dev generate-all --mode check; gaps are that some generated pages are kept in sync by tests instead of gen (docs/reference/languages.md from ~4M1BX5H), and there is no single list of every generated file. Route every generated file through the artifact registry (~11A603G), add a dry-run mode that prints the diff, and a generated-files manifest so CI and reviewers can see what is generated.
