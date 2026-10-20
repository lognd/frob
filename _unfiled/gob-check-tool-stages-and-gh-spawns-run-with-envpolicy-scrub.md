+++
id = "01M4DVX2H75D8GRGVSR93GY5TG"
title = "gob-check tool stages and gh spawns: run with EnvPolicy::Scrub (security.md 2.4)"
type = "task"
category = "todo"
priority = "low"
reporter = "lognd"
created = "2026-10-08T13:40:34Z"
updated = "2026-10-08T13:40:34Z"
labels = ["area:crunk"]
scope = ["crates/gob-check/src/tools.rs,crates/frob-gh/**"]
+++

Found while working ~S0S9G93: gob-exec now has EnvPolicy::Scrub and Runner::run_with_env, and only crunk-tailwind uses it. Tool stages (security.md 2.4) and gh spawns still inherit the whole environment; migrate them with a per-caller allowlist (GH_TOKEN as an explicit Spec::env addition for gh).
