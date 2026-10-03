+++
id = "01M4069XXM8A47Y1F88NWXQPMM"
title = "Artifact smoke script and fixture repository"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:59Z"
updated = "2026-10-03T13:43:17Z"
idempotency_key = "m2-rel-smoke-script"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/gob-dev/src/smoke.rs", "crates/gob-dev/tests/fixtures/smoke-repo/**", "packaging/smoke/**", "packaging/pypi/**", ".github/workflows/release.yml", "crates/frob-release/tests/release_workflow.rs", "docs/design/releases.md", "changelog.d/**"]

[[links]]
kind = "blocked-by"
target = "01M4069XMEQQ5P082TMA389FFK"

[[acceptance]]
text = "Given a built wheel, when cargo dev smoke runs, then doctor and check succeed on the fixture repository"
bound = true

[[acceptance]]
text = "Given a target on the exemption list, when smoke runs for it, then it reports skipped with the reason"
bound = false
+++

`cargo dev smoke --artifact PATH` installs a wheel into a clean venv (or unpacks a cargo-dist archive into a clean directory), then runs frob doctor and frob check on a copy of a tiny fixture repository (git-initialised in a temp dir) and asserts exit 0 and the JSON envelope shape. A target that cannot execute on its runner is an entry in a tested exemption list, never faked.
