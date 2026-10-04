+++
id = "01M41ZSW6DZMBE5QWNGB6VY10G"
title = "Test suite wall time is one test: split the real-repo perf test into a fixture test plus the scheduled bench, tune hot-crate opt-levels, enforce a per-test budget"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
reporter = "lognd"
created = "2026-10-03T22:57:50Z"
updated = "2026-10-04T00:54:18Z"
scope = ["crates/frob-check/tests/perf.rs", "crates/frob-check/benches/**", "crates/frob-check/Cargo.toml", "crates/gob-ir/tests/deep.rs", "crates/frob-ack/tests/workspace.rs", "Cargo.toml", ".config/nextest.toml", "crates/gob-dev/src/ci.rs", "docs/design/build-test-ci.md", "Cargo.lock"]

[[acceptance]]
text = "Given cargo nextest run --workspace --profile ci on the 12-core host, when it finishes, then the wall time is under 60 s and no test exceeds the per-test budget except named overrides"
bound = true

[[acceptance]]
text = "Given the perf assertions, when the fixture test runs, then it checks timed stages and warm cache hits in under 1 s"
bound = true

[[acceptance]]
text = "Given the scheduled bench, when it runs in release on this repository, then it reports cold and warm totals against the recorded budget"
bound = true
+++

Measured 2026-10-03 on the 12-core host, cargo nextest run --workspace --profile ci: 1355 tests, 138 s wall, 765 s of test time. The wall is one test:
- frob-check::perf warm_run_on_this_repository_produces_a_timing_breakdown: 98-136 s locally (243 s and a terminate once). It runs a cold then a warm full frob check on this whole repository in a debug build; the warm run is about 6 s, so the cold debug run is the cost. Its assertions (stages are timed, the warm run hits the cache) need no real repository.
- gob-ir::deep a_million_levels_deep_on_a_default_stack_is_total_and_deterministic: 57 s, the million-level model built twice at opt-level 0.
- next: frob-ack workspace test 16 s (also scans this workspace), two mdtest corpora 13 s and 9 s; frob-cli tests 3-6 s each from spawning the debug frob binary many times.

Fix structurally, not by marking tests ignored:
1. Split function from performance: the perf test's functional assertions run on a small fixture repository (well under 1 s); the real-repository cold and warm measurement moves to the criterion bench that build-test-ci.md 4 schedules ("bench (scheduled)"), in release, with recorded budgets (architecture.md 9: warm under 2 s), so a regression is a bench failure with a number, not a slow test. Same review for frob-ack's workspace test: if it needs the real workspace for a property, keep one, otherwise use a fixture.
2. Build profile: measure opt-level 1 (or 2) for the hot crates in the dev and test profiles via [profile.dev.package.<crate>] overrides (gob-ir at least; measure gob-symbols, frob-check and the frob binary too) against compile time with sccache; adopt what lowers total cargo dev ci time, record the numbers in build-test-ci.md. The deep test keeps its million levels (that is the property) but runs the model once and compares a digest for determinism if the second build adds nothing.
3. Guard: the nextest ci profile gets a per-test time budget that fails a test exceeding it (slow-timeout with terminate-after giving about 30 s), with a named, reviewed override list in .config/nextest.toml for any test that legitimately needs more; cargo dev ci reports the suite wall time and the five slowest tests.
