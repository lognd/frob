+++
id = "01M4069XRXTR0P7BE595Y75MX7"
title = "Release workflow wheel matrix: manylinux 2_28, macOS x86_64 cross-built on macos-latest"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:59Z"
updated = "2026-10-03T11:47:51Z"
idempotency_key = "m2-rel-wheel-matrix"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = [".github/workflows/release.yml", "packaging/pypi/build-wheel.sh", "packaging/pypi/smoke.sh", "packaging/pypi/BUILDING.md", "crates/frob-release/tests/release_workflow.rs", "crates/frob-release/Cargo.toml", "Cargo.lock"]

[[links]]
kind = "blocked-by"
target = "01M4069XFWGEFARNVXTXHT82FS"

[[links]]
kind = "blocked-by"
target = "01M4069XMEQQ5P082TMA389FFK"

[[acceptance]]
text = "Given a tag, when the matrix runs, then five wheels and one sdist exist as artifacts"
bound = true

[[acceptance]]
text = "Given the workflow, when grepped for macos-13 or manylinux auto, then there is no match"
bound = true
+++

Build jobs for the five wheel targets with maturin-action pinned by SHA; manylinux: 2_28 on both linux entries; the macOS x86_64 leg runs on macos-latest and cross-compiles; linux aarch64 is built by cross container and smoked on ubuntu-24.04-arm; every job has timeout-minutes; wheels uploaded as run artifacts.
