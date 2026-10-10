+++
id = "01M4K3BPQ72DVFEMK8EXQSD03K"
title = "experimental red: 5 CAP001 errors since ~2T7C4A9 (process.env ungranted in frob/gob/grimble/crunk, clap Command::new misread as process.spawn)"
type = "bug"
category = "in-progress"
priority = "critical"
points = 3
reporter = "Claude"
created = "2026-10-10T14:27:06Z"
updated = "2026-10-10T14:41:29Z"
scope = ["design/model.grmb", "crates/grimble-*/**"]

[[acceptance]]
text = "frob check on experimental reports 0 CAP001 errors"
bound = false

[[acceptance]]
text = "clap::Command::new is not observed as process.spawn (only std::process::Command is)"
bound = true

[[acceptance]]
text = "process.env reads are granted in design/model.grmb only where the code legitimately reads the environment"
bound = false
+++

found while coordinating the drain: after ~2T7C4A9 landed, frob check reports 5 CAP001 errors (design/model.grmb lines 5, 16, 16, 28, 39). Blocks every land via the base-red refusal.
