+++
id = "01M63G1NRAKZ4RGQBWNHQW3WE8"
title = "Grimble LOG rules: unsupported resolution classes (non-literal mode args, Rust macro_rules and extern C, Bash redirects, JS dynamic console[name])"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T09:32:21Z"
updated = "2026-11-06T23:46:48Z"
labels = ["no-story"]
scope = ["crates/grimble-check/src/log/**", "docs/design/grimble/output-atoms.md"]

[[acceptance]]
text = "LOG rules report non-constant open modes, run-time shell fd redirects and dynamic console[name] as unresolved, and scan Rust macro_rules bodies and extern C blocks"
bound = true
+++

found while working ~JKKJPTT: these forms are skipped; JS dynamic access has no flag_dynamic yet
