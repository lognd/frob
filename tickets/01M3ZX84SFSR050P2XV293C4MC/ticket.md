+++
id = "01M3ZX84SFSR050P2XV293C4MC"
title = "mirror resolve --keep-repo and --ignore-field, recorded as ledger events"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:43Z"
updated = "2026-10-03T03:39:11Z"
idempotency_key = "m2-mirror-resolve-basic"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob/src/mirror_cmd.rs", "crates/frob-ledger/src/event.rs"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ81430D3D5QSNCFM8QB0"

[[links]]
kind = "blocked-by"
target = "01M3ZX84HDHZCJRSXCCPNP7J3G"

[[acceptance]]
text = "Given MIR002 on a ticket, when `mirror resolve <ticket> --keep-repo` runs, then the repository version is republished and a resolution event with the resolver exists"
bound = false

[[acceptance]]
text = 'Given `--ignore-field priority --reason "owned in tracker"`, when run, then mirror.toml records it and the field is no longer compared'
bound = false
+++

Implements mirror.md section 3.1 (resolution verbs).

keep-repo republishes the repository version with a comment linking the edit; ignore-field --reason stops mirroring that field for that issue (recorded in mirror.toml); each is a ledger event with resolver and reason.
