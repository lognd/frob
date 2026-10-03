+++
id = "01M41B4KPWQVBT234N2DY20758"
title = "frob release notes: print one version's CHANGELOG section for gh release create"
type = "task"
category = "todo"
priority = "medium"
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T16:56:42Z"
updated = "2026-10-03T16:56:42Z"
idempotency_key = "m2-rel-notes-verb"
labels = ["milestone:2", "area:release"]
scope = ["crates/frob/src/release_cmd.rs", "crates/frob-release/src/changelog.rs", ".github/workflows/release.yml"]

[[acceptance]]
text = "Given a CHANGELOG with a section for version X, when frob release notes --version X runs, then it prints exactly that section body"
bound = false
+++

found while working ~DR38G0G: nothing exposes one version's section (changelog::split is library only, heading_version private), and the release job must not parse markdown in shell. Add the verb, then switch the release job from --generate-notes to --notes-file (unpack the linux archive's frob, or build it).
