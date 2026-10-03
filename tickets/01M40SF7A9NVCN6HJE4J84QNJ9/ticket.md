+++
id = "01M40SF7A9NVCN6HJE4J84QNJ9"
title = "Release workflow: pin rustup-init by hash in the manylinux container; record the no-sdist decision"
type = "task"
category = "in-progress"
priority = "low"
points = 1
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T11:47:55Z"
updated = "2026-10-03T19:22:24Z"
idempotency_key = "m2-rel-pin-rustup-init"
labels = ["milestone:2", "area:release", "area:security"]
scope = [".github/workflows/release.yml", "packaging/pypi/**", "docs/design/releases.md", ".github/workflows/build-smoke.yml", "crates/frob-release/tests/release_workflow.rs", "changelog.d/01M413T4GRZDC843XFPG31XEZ3.fixed.md", "changelog.d/01M40YQZF4422S88TN6992AN0Q.fixed.md"]

[[acceptance]]
text = "Given the release workflow, when read by the invariant test, then rustup-init and maturin are hash-pinned and the test fails if either is not"
bound = true
+++

From ~5Y75MX7: inside the manylinux_2_28 containers rustup-init is fetched from sh.rustup.rs unpinned (the toolchain version is pinned, the installer is not), and maturin is pinned by version without a hash. Download rustup-init from the versioned static URL and verify its sha256, and install maturin with --require-hashes from a pinned requirements file. Also add one line to docs/design/releases.md 6: no sdist (the wheel bundles binaries; source ships through crates.io and git).
