+++
id = "01M454HXEWGJM5MXTA2H2CEBV3"
title = "Linux wheel and smoke jobs fail linking gob-dev: mold and clang are not installed on the host"
type = "bug"
category = "in-progress"
priority = "high"
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-05T04:18:29Z"
updated = "2026-10-05T04:21:22Z"

[[acceptance]]
text = "Given the wheel and smoke jobs of build-smoke.yml on a Linux runner, when they build gob-dev with cargo dev, then mold and clang are installed first by the same local composite action ci.yml uses, with no copy of the install step"
bound = false

[[acceptance]]
text = "Given any workflow job that runs cargo build, run, test, nextest, clippy, doc, install or cargo dev on a possibly-Linux runner, when release_workflow tests run, then the test fails if the job has neither the linker action before that step nor the stock-linker override"
bound = true

[[acceptance]]
text = "Given the changed workflows, when zizmor and actionlint run, then both are clean"
bound = false
+++

Found on dry run 37261721862: both Linux wheel jobs fail at link time in the host-side cargo dev wheel-smoke build with clang: error: invalid linker name in argument -fuse-ld=mold. The repo cargo config links Linux with clang and mold; ci.yml installs them inline in the rust job, the wheel and smoke jobs of build-smoke.yml never do. Fix with one shared definition (a local composite action) used by ci.yml and build-smoke.yml, not a linker override, and add a release_workflow test that fails when a job compiles Rust on a Linux host without it.
