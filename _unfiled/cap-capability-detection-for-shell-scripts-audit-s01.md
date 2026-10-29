+++
id = "01M64VBRKZE3BBSQNX21PKHMPA"
title = "CAP: capability detection for shell scripts (audit s01)"
type = "story"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-10-29T22:09:21Z"
updated = "2026-10-29T22:09:21Z"
scope = ["crates/gob-languages/**", "crates/gob-symbols/**"]
+++

Split from PKW7X2J. Shell has no Language variant or grammar. Needs: grammar plus detect, command-word resolution through aliases, functions, source and PATH builtins (curl, wget, nc, rm, cat, env, eval, bash -c); expansions in command position are Unresolved. Pin audit case s01.
