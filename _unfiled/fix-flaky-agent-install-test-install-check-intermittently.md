+++
id = "01M7VVPVJKC85MRTP9BR9Z949A"
title = "Fix flaky agent_install test: install --check intermittently fails when frob init exits 4"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-20T06:53:38Z"
updated = "2026-11-20T06:53:38Z"
labels = ["good-first"]
scope = ["crates/frob/tests/it/agent_install.rs"]

[[acceptance]]
text = "Given the agent_install integration tests run in parallel on Windows, when install_check_writes_nothing_and_prints_the_plan runs 20 times in a row, then every run passes and frob init in the repo() helper never exits 4"
bound = false
+++

tmp

## Start here

- Files to read first: <TODO: list the files>
- Test command: <TODO: the command that runs the tests>
- Who to ask: <TODO: a handle or channel>
