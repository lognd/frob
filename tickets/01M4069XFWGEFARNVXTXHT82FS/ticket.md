+++
id = "01M4069XFWGEFARNVXTXHT82FS"
title = "cargo-dist configuration: five targets, tag trigger frob-v*, timeouts, pinned actions"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:59Z"
updated = "2026-10-03T06:34:10Z"
idempotency_key = "m2-rel-dist-config"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["dist-workspace.toml", ".github/workflows/release.yml", "Cargo.toml", "crates/frob/Cargo.toml", "docs/decisions/**"]

[[acceptance]]
text = "Given a frob-v tag push, when the workflow runs, then it builds archives for the five targets with timeouts on every job"
bound = false

[[acceptance]]
text = "Given the workflow file, when actionlint and zizmor run, then they report no finding"
bound = false
+++

Decision recorded in the ticket: cargo-dist builds the standalone binary archives and the GitHub release (monorepo.md 4); the PyPI wheel is built by maturin separately (next tickets). Targets x86_64 and aarch64 linux-gnu, aarch64 and x86_64 apple-darwin (x86_64 cross on macos-latest, never a retired image), x86_64 windows-msvc. Every job has timeout-minutes, every action pinned by SHA, permissions minimal, concurrency group release. Trigger is the frob-v* tag push only. Resolve whether the generated workflow can satisfy the SHA-pin and permission policy (cargo-dist allows customisation through custom jobs); if not, fall back to a hand-written matrix and say so in the ADR.
