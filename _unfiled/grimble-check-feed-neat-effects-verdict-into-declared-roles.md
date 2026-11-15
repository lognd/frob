+++
id = "01M7EXW4TZY9Z3EBVGENTF89BZ"
title = "grimble-check: feed NEAT effects verdict into declared_roles so grimble:shell can verify"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:21:21Z"
updated = "2026-11-15T06:21:21Z"
labels = ["no-story"]

[[acceptance]]
text = "A shell-claimed unit with clean effects is verified: true"
bound = false

[[acceptance]]
text = "A violating one is not"
bound = false
+++

Audit: /home/logan/projects/frob-audit-grimble-crunk.md M6. crates/grimble-check/src/unit_role.rs:75-98 always sets verified: false; see coh002.rs:418-421 and crates/grimble-lints/src/neat/effects.rs:201.
