+++
id = "01M7DEJYD4XMEPRQXPTRFY1X8T"
title = "ci: remove the crunk-parity job (user ruling)"
type = "task"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-14T16:34:56Z"
updated = "2026-11-14T16:35:25Z"
labels = ["no-story", "chore"]
scope = [".github/workflows/ci.yml"]

[[acceptance]]
text = "ci.yml has no crunk-parity job and docs/guides/crunk.md no longer says it runs in CI"
bound = false
+++

Owner ruled the Chromium parity check must not be a CI job. Remove the crunk-parity job from ci.yml and update docs/guides/crunk.md; the test stays runnable locally. No-story chore.
