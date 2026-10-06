+++
id = "01M47QV23EAN5DE6DDV9HS3VP7"
title = "cargo dev ecosystem: base vs PR finding diff over a pinned real-project corpus"
type = "story"
category = "todo"
priority = "high"
points = 8
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T04:34:07Z"
updated = "2026-10-06T04:34:07Z"
scope = ["crates/gob-dev/**", "ecosystem.toml", ".github/workflows/**"]

[[acceptance]]
text = "the report lists per-rule deltas, crashes and timing for at least five pinned projects"
bound = false

[[acceptance]]
text = "a crash in the head binary is reported, not hidden"
bound = false

[[acceptance]]
text = "the PR job comments without failing the run"
bound = false
+++

build-test-ci.md section 6, ruff ecosystem and ty mypy_primer. ecosystem.toml pins repositories by SHA (Rust, Python, TS/React, C#/Unity and this repository). cargo dev ecosystem builds the base and head binaries, runs frob, grimble and crunk check on each project, and reports per-rule added, removed and changed findings, crashes, Unresolved deltas and timing as markdown. A non-blocking PR job posts it as a comment; locally it runs on goway helpers.
