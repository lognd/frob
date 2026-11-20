+++
id = "01M7VVPZEQ31Q83Y1KQPJYN7BG"
title = "Fix flaky grimble-bind term_cache test: warm build counts folds from parallel tests"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-20T06:53:42Z"
updated = "2026-11-20T06:53:42Z"
labels = ["good-first"]
scope = ["crates/grimble-bind/tests/it/**"]

[[acceptance]]
text = "Given the grimble-bind it binary runs its tests in parallel, when warm_build_reads_terms_from_cache_without_parsing runs 20 times in a row, then every run passes with zero adapter folds counted"
bound = false
+++

tmp

## Start here

- Files to read first: <TODO: list the files>
- Test command: <TODO: the command that runs the tests>
- Who to ask: <TODO: a handle or channel>
