+++
id = "01M6Q7V69XRNRTPER59N8GZ2CF"
title = "Wire workspace_rust_error_facts into a check verb"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-06T01:33:49Z"
updated = "2026-11-06T02:27:06Z"
labels = ["no-story"]
scope = ["crates/frob/src/**", "crates/gob-symbols/src/**"]

[[acceptance]]
text = "Given a workspace, when a check verb runs, then it calls workspace_rust_error_facts"
bound = false
+++

Follow-up of ~42SZBGD acceptance 2. No story fits (label no-story): a check verb must call gob_symbols::pipeline::workspace_rust_error_facts; the owning check crate needs scoping first.
