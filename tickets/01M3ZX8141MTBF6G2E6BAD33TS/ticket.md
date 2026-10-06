+++
id = "01M3ZX8141MTBF6G2E6BAD33TS"
title = "Ticket branch: [tickets] branch knob and orphan-branch bootstrap"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:40Z"
updated = "2026-10-06T14:40:42Z"
idempotency_key = "m2-tb-config-init"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-ledger/src/branch.rs", "crates/frob/src/ticket/branch_cmd.rs", "crates/frob-ledger/src/lib.rs", "crates/frob/src/config.rs", "crates/frob/src/ticket/mod.rs", "crates/frob/tests/cli.rs", "crates/frob/tests/ticket_branch.rs", "changelog.d/*BAD33TS*", "docs/reference/config.md", "docs/schemas/config.json", "docs/reference/cli/frob.md", "docs/design/architecture.md", "crates/frob/tests/snapshots/cli__*.snap", "crates/frob-ledger/tests/branch.rs"]

[[acceptance]]
text = "Given a repository without the branch, when `frob ticket branch init` runs, then an orphan branch frob-tickets with a README placeholder exists and the code checkout is unchanged"
bound = true

[[acceptance]]
text = "Given the branch already exists, when run again, then the verb reports already and changes nothing"
bound = true
+++

Implements mirror.md section 1; tickets.md (ledger ref, D23).

Materialized [tickets] branch (default frob-tickets); `frob ticket branch init` creates the orphan branch through gob-git commit_paths with CAS so the code checkout is untouched; the existing [tickets] ref knob points at it.
