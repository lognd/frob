+++
id = "01M7VVPVJKC85MRTP9BR9Z949A"
title = "Fix flaky agent_install test: install --check intermittently fails when frob init exits 4"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-20T06:53:38Z"
updated = "2026-11-20T06:53:55Z"
labels = ["good-first"]
scope = ["crates/frob/tests/it/agent_install.rs"]

[[acceptance]]
text = "Given the agent_install integration tests run in parallel on Windows, when install_check_writes_nothing_and_prints_the_plan runs 20 times in a row, then every run passes and frob init in the repo() helper never exits 4"
bound = false
+++

The test install_check_writes_nothing_and_prints_the_plan in crates/frob/tests/it/agent_install.rs is flaky on Windows: it sometimes fails because `frob init` exits 4 instead of 0. Every `run()` call builds a fresh git repo and runs `frob init` through the `repo()` helper (assert_eq status 0), so the failure is in that setup assert, not in the --check logic. The cause is not yet known; suspect parallel tests contending on a shared resource (a lock, a cache or config dir, or antivirus on tempdirs).

## Start here
- Files to read first: crates/frob/tests/it/agent_install.rs (the repo() helper), crates/frob/tests/it/common (git_repo, frob_command), and the init verb exit codes.
- Test command: cargo nextest run -p frob -E "test(install_check_writes_nothing_and_prints_the_plan)" with CARGO_BUILD_JOBS=2.
- Goal: print init stderr on failure to find the cause, then fix it (retry-free) so the test is stable.
no-story: internal test-reliability task; it has no direct user-visible outcome of its own.
