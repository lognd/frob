+++
id = "01M4CTTTCNT71XQFM9257AZHYH"
title = "Release for non-Rust projects: cut never rewrites Cargo layout unasked, bump updates pyproject.toml, status has no frob-specific items"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M4CTTPJ00PTDE0A1SE4MJFCF"
reporter = "lognd"
created = "2026-10-08T04:02:37Z"
updated = "2026-10-09T04:54:23Z"
scope = ["changelog.d/**", "crates/frob-release/**", "docs/guides/release.md"]

[[acceptance]]
text = "Given a Python project, when frob release bump and cut run, then pyproject.toml's version changes and no Cargo file is created or rewritten"
bound = false

[[acceptance]]
text = "Given a project without [release] registry settings, when release status runs, then no frob-specific item appears"
bound = false

[[acceptance]]
text = "Given a non-Rust project whose pyproject name is logand-app, when REL002 runs, then it names the package by its pyproject name and does not require Cargo.toml/pyproject lockstep unless the project declares it (logand.app-v2 F-505)"
bound = false
+++

notes/review/adoption-trial-2026-10-07.md HIGH 4: release cut rewrote the Cargo layout into workspace.package plus version.workspace; bump does not touch pyproject.toml; release.md only covers frob; release status lists frob's own registry and PyPI trusted publishing items in an unrelated project. Version files come from detected manifests (Cargo, pyproject, package.json) declared in [release]; frob-specific readiness items move behind config this repository sets.
