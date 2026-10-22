+++
id = "01M5J45YZ60A5R1DWZG2ZQDW75"
title = "frob-obligations corpus mdtest: doc002.md fails 7 of 19 DOC002 cases on experimental"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T15:37:53Z"
updated = "2026-10-22T16:14:19Z"
scope = ["crates/frob-obligations/**", "docs/reference/rules/DOC002.md", "crates/gob-check/src/applicability.rs", "changelog.d/01M5J45YZ60A5R1DWZG2ZQDW75.fixed.md"]

[[acceptance]]
text = "Given the corpus mdtest, when it runs, then every case in doc002.md passes"
bound = true
+++

cargo test -p frob-obligations --test corpus fails on experimental: the 'fires' cases in tests/mdtest/doc002.md (missing file, missing heading, path leaving the repo, root-relative, nested fence, language matrix) do not fire. Reproduces with the JSMN4BH changes stashed, so it predates them. Find the cause (fixture lookup, rule wiring or the test harness) and fix.
