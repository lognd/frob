+++
id = "01M42A37XTPF2H1WXQQZWEYXGZ"
title = "cargo dev ci can run its heavy steps on a goway host (opt-in), keeping the step list the single source"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-04T01:57:43Z"
updated = "2026-10-04T04:24:25Z"
scope = ["crates/gob-dev/src/ci.rs", "crates/gob-dev/tests/**", "docs/design/build-test-ci.md", "CONTRIBUTING.md"]

[[acceptance]]
text = "Given --remote and a fake goway that records its argv, when cargo dev ci runs, then offloadable steps call goway run with the exact argv and env of the step and the summary names the host"
bound = false

[[acceptance]]
text = "Given goway exits 125, when a remote step runs, then the summary reports a goway failure distinct from a test failure"
bound = false
+++

The owner's goway dev build (~/.local/opt/goway-dev/current/goway, LAN helpers quasar and xanders-laptop, x86_64 Linux) ran frob-v2's suite remotely: 1383 of 1385 pass, the 2 needing .git until goway's --with-git. Offloading the heavy steps (nextest, clippy for the Windows target, docs) frees the aarch64 laptop that runs many agent builds.

Add an opt-in to cargo dev ci: --remote (or CARGO_DEV_CI_REMOTE=<goway binary>) runs each step marked offloadable through goway run --report with the same argv and env as the local step, so the step list in ci.rs stays the single source and the parity test still holds. It streams output, uses the command's exit code (125 from goway itself is a distinct failure naming goway), and prints the host and arch per step in the summary. Steps that need the local .git (doctor, check, the two .git-dependent tests) stay local, or pass goway's --with-git once it exists. Steps keep their declared prerequisites, checked on the remote through goway doctor when available. Default stays local; CI never uses it.
