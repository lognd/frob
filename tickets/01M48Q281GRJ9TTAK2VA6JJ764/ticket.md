+++
id = "01M48Q281GRJ9TTAK2VA6JJ764"
title = "Trim the read verbs per D104, with one-minor hidden aliases"
type = "story"
category = "todo"
priority = "high"
parent = "01M48Q27GE8C1P6JS1CXKTCQ3S"
reporter = "lognd"
created = "2026-10-06T13:39:48Z"
updated = "2026-10-06T13:39:48Z"
scope = ["crates/frob/**", "crates/frob-ledger/**", "crates/frob-lease/**", "crates/frob-worktree/**", "docs/**"]

[[acceptance]]
text = "each folded verb's behaviour and JSON is reachable through its new form (tests moved, not deleted)"
bound = false

[[acceptance]]
text = "each old spelling still works, is hidden from help, and prints the deprecation note"
bound = false

[[acceptance]]
text = "generated CLI reference lists only the new forms"
bound = false
+++

Fold `ticket brief` into `ticket show --format md`, `ticket triage list` into `ticket list --category triage`, `ticket contention` into `lease list --contention`, `start` into `work --here`. Each removed spelling stays as a hidden alias for one minor release that prints a one-line deprecation note on stderr naming the new form; generated CLI docs and agent-facing docs (CLAUDE.md templates, guides) use only the new forms.
