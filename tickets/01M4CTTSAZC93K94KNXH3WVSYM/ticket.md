+++
id = "01M4CTTSAZC93K94KNXH3WVSYM"
title = "Ticket-branch mode for adopters: work builds the worktree from the code branch, ref_mode names the orphan branch, setup documented"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M4CTTPJ00PTDE0A1SE4MJFCF"
reporter = "lognd"
created = "2026-10-08T04:02:36Z"
updated = "2026-10-10T00:44:34Z"
scope = ["changelog.d/**", "docs/design/tickets.md", "crates/frob-ledger/src/config.rs", "crates/frob-ledger/src/error.rs", "crates/frob-ledger/src/layout.rs", "crates/frob-ledger/src/ledger.rs", "crates/frob-ledger/src/lib.rs", "crates/frob-ledger/src/scrub.rs", "crates/frob-ledger/src/triage.rs", "crates/frob-pm/src/store.rs", "crates/frob-evidence/src/workspace.rs", "crates/frob-worktree/src/config.rs", "crates/frob/src/config.rs", "crates/frob/src/init.rs", "crates/frob/tests/doc_commands.rs", "crates/frob/tests/e2e_init_loop.rs", "crates/frob/tests/snapshots/cli__init_frob_toml.snap", "docs/guides/ticket-branch.md", "docs/reference/config.md", "docs/reference/cli/frob.md", "docs/schemas/config.json"]

[[links]]
kind = "relates"
target = "01M3ZX82YQ43A8SWS4F128J4NT"

[[acceptance]]
text = "Given a repository whose ledger lives on an orphan ticket branch, when frob work and frob land run, then the worktree is built from the code base branch and the land succeeds"
bound = false

[[acceptance]]
text = "Given docs/guides, when read, then a ticket-branch setup section exists and its commands pass in a fresh repository (doc test)"
bound = false
+++

notes/review/adoption-trial-2026-10-07.md HIGH 3: ref_mode=branch means the checked-out code branch; the orphan branch needs ref=refs/heads/frob-tickets; then frob work builds the worktree from the tickets-only branch (no code, no frob.toml) and land fails E-NO-CONFIG. Coordinate with the ticket-branch chain (~128J4NT and its blockers): read their tickets first and land in their order, or merge into them if they already cover a piece.
