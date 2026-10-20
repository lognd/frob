+++
id = "01M42A37XTPF2H1WXQQZWEYXGZ"
title = "cargo dev ci can run its heavy steps on a goway host (opt-in), keeping the step list the single source"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-04T01:57:43Z"
updated = "2026-10-04T05:40:58Z"
scope = ["crates/gob-dev/src/ci.rs", "crates/gob-dev/tests/**", "docs/design/build-test-ci.md", "CONTRIBUTING.md"]

[[acceptance]]
text = "Given --remote and a fake goway that records its argv, when cargo dev ci runs, then offloadable steps call goway run with the exact argv and env of the step and the summary names the host"
bound = true

[[acceptance]]
text = "Given goway exits 125, when a remote step runs, then the summary reports a goway failure distinct from a test failure"
bound = true
+++

Plan (revised): offload clippy, clippy-windows, docs, nextest, doctor and check through goway run --with-git (minimal .git, so doctor/check run remotely); fmt, gen, zizmor, actionlint and test --dry-run stay local. Opt-in via CARGO_DEV_CI_REMOTE=<goway binary> now; the --remote flag is ~3WK9JKE (main.rs is leased elsewhere). Needs go to goway as separate argv. Exit 125 retries with backoff then reports GOWAY, distinct from FAILED. --report gives host, os, arch, exit, duration for the summary. RemoteOs holds OS-specific terms so --remote-os windows can be added later (not built). Prerequisites are probed on the host and the step is pinned to it. Default stays local; CI never uses it.
