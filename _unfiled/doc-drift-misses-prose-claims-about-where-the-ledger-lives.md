+++
id = "01M5XEHTWZCVB76SEMR4ZWVCR7"
title = "Doc drift misses prose claims about where the ledger lives (no binding from README/guides to ledger code)"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-27T01:10:47Z"
updated = "2026-10-27T01:10:47Z"
scope = ["crates/frob-check/**", "docs/design/**"]

[[acceptance]]
text = "a rule or binding flags docs that name a path the repo no longer has or that contradicts [tickets] ref_mode"
bound = false
+++

DRIFT001 only fires on frob:doc/describes bindings; README, quickstart and CONTRIBUTING had none, so the move to the orphan ledger left them stale unflagged. Consider DOC rule for backticked paths absent from the tree, and bindings from ledger docs to crates/frob-ledger config.
