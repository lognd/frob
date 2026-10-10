+++
id = "01M4M0ABX9R9J96C1CF1PSGNZP"
title = "nested nextest runs inherit an undefined NEXTEST_PROFILE and exit 96 under CI"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-10T22:53:10Z"
updated = "2026-10-10T22:55:18Z"
scope = ["crates/frob-evidence/src/provider.rs", "crates/frob-tests/tests/rust_root.rs"]

[[acceptance]]
text = "a_crate_under_a_subdirectory_runs_nextest_from_that_directory passes with NEXTEST_PROFILE=ci inherited"
bound = true

[[acceptance]]
text = "a_runner_that_fails_before_running_tests_shows_its_stderr_tail_and_exit_code passes with NEXTEST_PROFILE=ci inherited"
bound = true
+++

CI runs cargo nextest run --profile ci, which exports NEXTEST_PROFILE=ci to test processes. frob test with no [evidence] nextest_profile passes no --profile, so the nested nextest of a crate without a ci profile inherits it and exits 96 (profile 'ci' not found). Product fix: when an inherited NEXTEST_PROFILE names a profile the project config does not define, run with the default profile.
