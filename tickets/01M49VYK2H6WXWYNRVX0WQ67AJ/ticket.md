+++
id = "01M49VYK2H6WXWYNRVX0WQ67AJ"
title = "CLI: deprecated aliases as a compile-checked #[command(deprecated = ...)] attribute; --format md refused on verbs without a markdown view"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
parent = "01M48Q27GE8C1P6JS1CXKTCQ3S"
reporter = "lognd"
created = "2026-10-07T00:24:26Z"
updated = "2026-10-07T03:58:57Z"
scope = ["crates/gob-cli/**", "crates/gob-macros/**", "crates/frob/**", "crates/frob-check/src/verb.rs", "crates/frob-lease/src/verbs.rs", "crates/frob-worktree/src/verbs.rs", "crates/gob-product/src/*.rs"]

[[acceptance]]
text = "a deprecated alias is declared by the attribute and a target that is not a registered verb fails (test)"
bound = true

[[acceptance]]
text = "the md format on a verb without a markdown view is a usage error naming the supporting verbs"
bound = true

[[acceptance]]
text = "no code parses a doc summary prefix for deprecation"
bound = true
+++

Follow-up to ~A6JJ764 (D104): (1) a deprecated alias is recognised today by its doc summary starting with 'Deprecated alias of', a string convention where a typo silently un-hides the verb; move it to #[command(deprecated = "<new form>")] on the Command derive, validated at expansion (the target form must name a registered verb), and delete the prefix parsing. (2) --format md is global and silently falls back to text on verbs without a markdown view; refuse it with a usage error naming the verbs that support it (fail loudly).
