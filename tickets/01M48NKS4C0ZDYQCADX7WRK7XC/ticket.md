+++
id = "01M48NKS4C0ZDYQCADX7WRK7XC"
title = "Config-references-rules consistency test: every rule id or slug named in config exists or redirects"
type = "task"
category = "todo"
priority = "low"
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T13:14:26Z"
updated = "2026-10-06T13:14:26Z"
scope = ["crates/gob-config/**", "crates/gob-rules/**", "crates/frob/**"]

[[acceptance]]
text = "a config naming an unknown rule id fails the test naming the file and key"
bound = false

[[acceptance]]
text = "a renamed rule id named in config resolves through the redirect table and passes"
bound = false

[[acceptance]]
text = "frob doctor reports an unknown rule id in a user repository's config"
bound = false
+++

Source review N5 (notes/research/codegen-macros.md G11, clippy tests/config-consistency.rs): config names rule ids (crunk.toml [lint] COLOR001 = off, frob.toml rule severities and exceptions, directive waivers name rules). Add a registry-driven test over every ConfigTable field and shipped config that takes rule ids or slugs, failing on an unknown id that is neither live nor a redirect (~67J8R53), plus the same check as a doctor/config finding for user repositories.
