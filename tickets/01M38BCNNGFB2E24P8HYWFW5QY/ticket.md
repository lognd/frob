+++
id = "01M38BCNNGFB2E24P8HYWFW5QY"
title = "land: reuse built native extensions when the crate tree hash is unchanged"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5808"]
labels = ["milestone:v0.534.0"]
scope = ["src/frob/natives/_build.py", "tests/unit/test_natives_build.py", "docs/modules/cli.md", "frob.lock"]
+++

Measured on every land today: "worktree natives stale/unimportable after
auto-rebuild attempt (T-1578)" followed by a maturin build of
strata_core and frob_core, 70-190 s per land, even when the worktree's
Rust sources are byte-identical to the root's already-built extension.
Fix: stamp each built extension with the git tree hash of its crate
source (`git rev-parse HEAD:strata-core/src`, same for frob-core) plus
the toolchain id; at land (and in `frob natives build`), when the
worktree's crate tree hash equals the stamp of an importable build in
the root venv (or the worktree's own venv), copy/reuse that artifact
instead of rebuilding; rebuild only on hash mismatch or import failure.
Positive control: two consecutive lands of worktrees with identical
crate trees must show one build and one reuse in the log; a worktree
that changes strata-core/src must rebuild. Owner directive: guaranteed-
safe automation runs automatically and is logged.
