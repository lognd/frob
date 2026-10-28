+++
id = "01M5XEHTWZCVB76SEMR4ZWVCR7"
title = "Docs must be bound and their backticked paths must exist (error rules)"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-27T01:10:47Z"
updated = "2026-10-28T12:55:43Z"
labels = ["no-story"]
scope = ["crates/frob-check/**", "docs/design/**", "crates/frob-rules/**", "README.md", "CONTRIBUTING.md", "docs/**", "**/*.md"]

[[acceptance]]
text = "a rule or binding flags docs that name a path the repo no longer has or that contradicts [tickets] ref_mode"
bound = false

[[acceptance]]
text = "A DOC rule at severity error flags any docs/ page, README or CONTRIBUTING with no frob:describes or frob:doc binding; existing unbound pages are bound in the same change"
bound = false

[[acceptance]]
text = "A DOC rule at severity error flags backticked repo paths in docs that do not exist, mirroring the existing flag and command check; a frob:legacy marker exempts deliberate legacy descriptions"
bound = false

[[acceptance]]
text = "The ledger docs (README, quickstart, ticket-branch, CONTRIBUTING) are bound to the [tickets] config and crates/frob-ledger code"
bound = false

[[acceptance]]
text = "Both rules cover every markdown file in the repo (not only docs/, README, CONTRIBUTING) and documentation comments in all supported languages (rustdoc, docstrings, JSDoc, XML doc), via the same binding and path checks"
bound = false

[[acceptance]]
text = "Both rules can be waived per site with frob:waive and a reason; a waiver without a reason is itself an error"
bound = false
+++

DRIFT001 only fires on frob:doc/describes bindings; README, quickstart and CONTRIBUTING had none, so the move to the orphan ledger left them stale unflagged. Consider DOC rule for backticked paths absent from the tree, and bindings from ledger docs to crates/frob-ledger config.

no-story: internal engineering task in frob-check; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
