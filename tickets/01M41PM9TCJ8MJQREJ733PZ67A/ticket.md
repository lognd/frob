+++
id = "01M41PM9TCJ8MJQREJ733PZ67A"
title = "Ledger events commit absolute local paths (home directory, user name) into pushed repositories"
type = "security"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-03T20:17:30Z"
updated = "2026-10-03T20:44:11Z"
scope = ["crates/frob-worktree/src/work.rs", "crates/frob-lease/src/model.rs", "crates/frob-evidence/**", "crates/frob-obligations/**", "crates/frob-ledger/src/rules.rs", "crates/frob-ledger/src/privacy.rs", "crates/frob-ledger/src/lib.rs", "crates/frob-ledger/tests/privacy.rs", "crates/frob-check/src/product.rs", "crates/frob-tests/src/verb.rs", "docs/reference/rules/TICK004.md", "docs/reference/rules/README.md", "crates/frob-worktree/tests/work.rs", "docs/design/tickets.md"]

[[acceptance]]
text = "Given frob work in a worktree under the home directory, when the lease event is written, then it contains no absolute path, only the worktree relative to the repository parent"
bound = true

[[acceptance]]
text = "Given a provider whose output contains the absolute worktree path and the home directory, when evidence is recorded, then the event contains placeholders and no absolute path"
bound = false

[[acceptance]]
text = "Given a committed ledger file containing /home/name/, when frob check runs, then the new rule reports it with a remedy, and a clean ledger reports nothing"
bound = false
+++

Reported by goway (2026-10-03, FROB_FEEDBACK item 4): frob work writes tickets/<id>/events/<ulid>.toml with reason = "lease: <actor> in /home/<user>/projects/<repo>-wt/<TICKET>; scope: ...; ttl ...". Ledger events are committed and pushed, so every public repository leaks the local user name and directory layout. This repository's pushed experimental branch has 246 ledger files with /home/logan paths (lease reasons, and evidence and test output that embed worktree paths such as /home/logan/projects/frob-v2-wt/7HWFTBP/crates/frob-pm).

Fix at every place frob writes text into the ledger:
1. Lease events (crates/frob-worktree/src/work.rs, the "lease: {} in {}" format, and anything in frob-lease/src/model.rs) record the worktree relative to the repository's parent directory (for example frob-v2-wt/7HWFTBP), never an absolute path. The live lease registry under .git/ is local and may keep absolute paths.
2. Captured evidence text (tool output, transcripts, refs) has absolute paths under the repository root, the worktree root and the user's home directory rewritten to placeholders (<repo>/, <worktree>/, ~/) before it is written, at the single point where captured text enters an event (the same place ~G31XEZ3 escapes non-ASCII). Digests must be computed consistently with what is stored; say which.
3. A check rule (new id in the ledger family; pick the next free TICK number and register it) flags any committed ledger file containing an absolute home path (/home/<name>/, /Users/<name>/, C:\Users\<name>\ and the like), with a remedy. Existing ledgers are not rewritten by frob; the rule reports them so the owner decides.
