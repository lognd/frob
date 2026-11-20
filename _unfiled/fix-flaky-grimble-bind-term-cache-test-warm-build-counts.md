+++
id = "01M7VVPZEQ31Q83Y1KQPJYN7BG"
title = "Fix flaky grimble-bind term_cache test: warm build counts folds from parallel tests"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-20T06:53:42Z"
updated = "2026-11-20T06:53:56Z"
labels = ["good-first"]
scope = ["crates/grimble-bind/tests/it/**"]

[[acceptance]]
text = "Given the grimble-bind it binary runs its tests in parallel, when warm_build_reads_terms_from_cache_without_parsing runs 20 times in a row, then every run passes with zero adapter folds counted"
bound = false
+++

The warm_build_reads_terms_from_cache_without_parsing test in crates/grimble-bind/tests/it/term_cache.rs is flaky. It asserts `folds == 0` using the process-wide `adapter_folds()` counter. Its SERIAL mutex only serialises the tests inside term_cache.rs, but since the tests were folded into the single `it` binary, other modules (for example warm_cache.rs) also call Code::build_with and fold in parallel, which can bump the counter during the measured window. This is the suspected cause.

## Start here
- Files to read first: crates/grimble-bind/tests/it/term_cache.rs and crates/grimble-bind/tests/it/warm_cache.rs (both build Code and fold), and adapter_folds in crates/grimble-bind/src/code.rs.
- Test command: cargo nextest run -p grimble-bind -E "test(term_cache)" with CARGO_BUILD_JOBS=2.
- Goal: make the fold-count measurement immune to other tests, for example share the SERIAL lock with warm_cache.rs or use a per-build counter, then confirm 20 repeat runs pass.
no-story: internal test-reliability task; it has no direct user-visible outcome of its own.
