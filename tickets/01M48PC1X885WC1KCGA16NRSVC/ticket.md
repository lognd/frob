+++
id = "01M48PC1X885WC1KCGA16NRSVC"
title = "gob-mdtest: failure UX: md file:line, rerun hint, filter env, GitHub annotations, one test per file"
type = "story"
category = "todo"
priority = "low"
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T13:27:41Z"
updated = "2026-10-06T13:27:41Z"
scope = ["crates/gob-mdtest/**", "crates/gob-dev/src/ci.rs"]

[[acceptance]]
text = "line mapping self-test"
bound = false

[[acceptance]]
text = "nextest lists one test per corpus file"
bound = false

[[acceptance]]
text = "the CI step emits annotations"
bound = false
+++

Report failures at path.md:LINE of the marker, print a rerun command, add a filter env (section path substring), emit GitHub annotations when requested, and generate one test per markdown file so nextest isolates and retries per file (ty datatest-style). Source: notes/research/rule-testing.md (D103).
