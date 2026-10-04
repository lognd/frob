+++
id = "01M42026M27TR9YV0C60JTYGH0"
title = "crates.io first publish of 31 new names hits the new-crate rate limit: handle 429, add a paced name-reservation mode, decouple PyPI from crates"
type = "story"
category = "todo"
priority = "high"
points = 5
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T23:02:23Z"
updated = "2026-10-03T23:02:23Z"
scope = ["crates/gob-dev/src/publish.rs", "crates/gob-dev/src/main.rs", ".github/workflows/release.yml", "crates/frob-release/tests/release_workflow.rs", "docs/guides/release.md", "docs/design/releases.md"]

[[acceptance]]
text = "Given the registry answers 429 with a retry time, when publish runs within its wait budget, then it waits and continues; past the budget it exits resumably naming the next crate and the retry time"
bound = false

[[acceptance]]
text = "Given publishable names missing from crates.io, when cargo dev publish --reserve runs without --apply, then it lists them and the pacing plan and publishes nothing"
bound = false

[[acceptance]]
text = "Given the release workflow, when the workflow test runs, then pypi does not need crates and both still need smoke"
bound = false
+++

Owner hit the crates.io rate limit while reserving names. State 2026-10-03: 35 crates are publishable; gob-macros, gob-rules, grimble (and crunk, not in this workspace) are reserved at 0.0.0 by the owner; the other 31 names are free, so the first release publishes 31 new crates. crates.io rate-limits new crate names much more tightly than new versions (a small burst, then on the order of one new crate per ten minutes; it answers 429 with the time to retry). cargo dev publish has no rate-limit handling, the crates job has a 120-minute timeout, and the pypi job needs crates, so the first tag would fail partway and block PyPI for hours.

1. cargo dev publish handles 429: parse the retry time crates.io returns (Retry-After header or the 'try again after <date>' message), wait within a --max-wait budget, and continue; when the budget is spent, exit with a resumable status naming the next crate and the earliest retry time. Test with the injected registry fake (no network).
2. cargo dev publish --reserve: publish a minimal 0.0.0 placeholder (name, description pointing at the repository, license, no code) for every publishable name not yet on crates.io, paced to the new-crate limit, resumable, dry-run by default and --apply to publish; the owner runs it once with their own token before the first release so the release publishes only new versions. Document it in docs/guides/release.md one-time setup.
3. The pypi job no longer needs crates: PyPI and crates.io publish independently after smoke (keep both behind their environments); update the workflow tests and the runbook.
