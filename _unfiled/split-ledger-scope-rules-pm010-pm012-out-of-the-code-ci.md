+++
id = "01M7EX8YQZ49F0WKXTC38B3Z4A"
title = "split ledger-scope rules (PM010-PM012) out of the code CI verdict"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:10:52Z"
updated = "2026-11-15T06:10:52Z"
labels = ["no-story"]

[[acceptance]]
text = "A PM010 failure does not change the code CI verdict (test)"
bound = false
+++

Source: frob-audit-meta.md M2. Evidence: ledger-only rule failures turn the code CI verdict red and block lands. Remedy: report them in a separate ledger verdict. Files: crates/frob-land/src/base_ci.rs, .github/workflows/ci.yml, rule scoping.
