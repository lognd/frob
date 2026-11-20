+++
id = "01M7X35W2WATD06TP58JC8MS7H"
title = "Audit 2026-11-20 refactor batch: one git spawn helper, one node_modules walk, verb-checked remedies"
type = "chore"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-20T18:23:24Z"
updated = "2026-11-20T18:23:24Z"
scope = ["crates/gob-git/**", "crates/frob-evidence/**"]

[[acceptance]]
text = "Given the ten hand-rolled git spawns, when migrated, then they go through one gob-git helper that the spawn counter sees and no Program::Git Spec is built outside gob-git"
bound = false

[[acceptance]]
text = "Given the four node_modules walk-ups, when unified, then one bounded helper serves them and a node_modules above the root is not found; given RemedyCommand strings, then a test checks each names a real verb"
bound = false
+++

Findings: Program::Git Spec built by hand at frob-worktree evict.rs:292 work.rs:935 gc/git.rs:19, frob init.rs:485, gob-dev ecosystem/run.rs:56 profile/fixture.rs:42, gob-git fallback.rs:27, frob-land git.rs:50 (8 distinct timeout consts); node_modules walk at frob-evidence provider.rs:863 and :888, coverage/js.rs:172, crunk-tailwind runtime/resolve.rs:17 (no root bound); 57 RemedyCommand::new(frob, verb) call sites. Do the is_ident dedupe NOT as a merge: the nine copies differ on purpose, rename them to say what they accept.
