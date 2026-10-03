+++
id = "01M41KT4RMYMMP9SSFN8RZK7QV"
title = "Closing a ticket as invalid, duplicate or wont-fix demands measured evidence and a changelog fragment"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-03T19:28:16Z"
updated = "2026-10-03T19:28:38Z"
scope = ["crates/frob-evidence/src/done.rs", "crates/frob/src/ticket/**", "crates/frob/tests/close_guards.rs"]

[[acceptance]]
text = "Given an open bug with no evidence, when ticket close --outcome invalid --reason R runs, then it closes without --no-evidence or --no-changelog"
bound = false

[[acceptance]]
text = "Given an open bug with no evidence, when ticket close --outcome fixed runs, then it is still refused with E-EVIDENCE-MISSING"
bound = false
+++

Observed 2026-10-03: ticket close ~28XNB4W --outcome invalid refused with E-EVIDENCE-MISSING ('closing (bug) needs at least one measured evidence record'), so dropping a non-bug needed --no-evidence --no-changelog with reasons. Evidence and changelog guards prove that a change was made; they apply to outcomes done and fixed only. invalid, duplicate and wont-fix close with a required --reason (already recorded) and no evidence or fragment. Check every done_requires predicate and the bug-evidence guard against the outcome in one place.
