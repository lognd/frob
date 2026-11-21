+++
id = "01M7YD43REEWDDYFCC3XDC1K0J"
title = "A frob:tests comment inside a function body detaches PATH001 accepts elsewhere in the file and reports findings at wrong lines"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-21T06:36:26Z"
updated = "2026-11-21T06:36:26Z"
labels = ["no-story"]
scope = ["crates/gob-directives/**"]

[[acceptance]]
text = "Given a test file where one function carries a frob:tests comment inside its body, when frob check runs, then accepts on other functions still suppress their findings and any finding reports its true line"
bound = false
+++

Found 2026-11-21: appending a test with an in-body frob:tests comment to crates/frob-evidence/tests/it/evidence.rs made PATH001 fire at lines 760-765 (true literals sit at 779-781, under a frob:accept). Moving the comment above the attribute cleared it (f6a81ae014). Either reject or correctly scope in-body directives, and fix the line attribution. no-story: lint bug.
