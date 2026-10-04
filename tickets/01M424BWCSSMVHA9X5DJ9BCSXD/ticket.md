+++
id = "01M424BWCSSMVHA9X5DJ9BCSXD"
title = "cargo dev builds the workspace twice (target/dev-tool, 2.7 GB per checkout); replace the separate target dir with a self-copy re-exec on Windows"
type = "task"
category = "in-progress"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-04T00:17:35Z"
updated = "2026-10-04T01:35:22Z"
scope = [".cargo/config.toml", "crates/gob-dev/src/**", "crates/gob-dev/tests/ci_parity.rs", "docs/design/build-test-ci.md"]

[[acceptance]]
text = "Given the dev alias, when cargo dev gen all runs after a code change, then the workspace is compiled once, into target/"
bound = false

[[acceptance]]
text = 'Given Windows, when cargo dev ci rebuilds the workspace, then gob-dev runs from a temporary copy and the build can replace target\\debug\\gob-dev.exe'
bound = false
+++

~0G8QF7V moved the dev alias to run -p gob-dev --target-dir target/dev-tool so a running target\\debug\\gob-dev.exe is never replaced on Windows while cargo dev ci rebuilds the workspace. gob-dev depends on frob-cli, so this compiles nearly the whole workspace a second time after every code change: target/dev-tool is 2.7 GB in the primary checkout and again in every ticket worktree (disk guard pressure), and cargo dev gen all waits on that second build. Owner reports gen all as slow. Fix: the alias goes back to the shared target dir (run -p gob-dev --), and gob-dev, on Windows only, before running any step that rebuilds the workspace, copies its own executable to a temp file and re-executes from there (the self-copy pattern), passing the arguments through and cleaning up the copy; Unix needs nothing (a running binary can be replaced). Update the regression test from ~0G8QF7V to assert the new mechanism instead of the separate target dir, and the CI design text. Measure: disk use per checkout and the time of cargo dev gen all after a one-line change, before and after.
