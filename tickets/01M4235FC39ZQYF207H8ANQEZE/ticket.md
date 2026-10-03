+++
id = "01M4235FC39ZQYF207H8ANQEZE"
title = "frob release adopt VERSION: record an existing published tag as a cut instead of deleting it (REL001)"
type = "story"
category = "todo"
priority = "critical"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T23:56:36Z"
updated = "2026-10-03T23:56:36Z"
scope = ["crates/frob-release/**", "crates/frob/src/release_cmd.rs", "crates/frob/tests/release.rs", "crates/frob/tests/release_cut.rs", "docs/design/releases.md", "docs/guides/release.md", "docs/reference/cli/frob.md", "docs/reference/rules/REL001.md"]

[[acceptance]]
text = "Given a pushed tag v0.1.0 cut by hand, when frob release adopt 0.1.0 runs, then a cut event marked adopted is recorded, git and the remote are untouched, and REL001 is clean"
bound = false

[[acceptance]]
text = "Given an adopted version, when adopt runs again, then it returns already and writes nothing"
bound = false

[[acceptance]]
text = "Given a tag with no cut, when REL001 reports it, then the remedy names frob release adopt first"
bound = false
+++

Reported by cloc (FROB_FEEDBACK item 14, 2026-10-03): after ~B5DF7DD made the tag pattern configurable, REL001 recognizes cloc's hand-cut, pushed and published tags v0.1.0 and v0.1.1 and reports "no recorded release cut; delete the tag and run frob release cut". Deleting published tags is destructive and outward-facing, and the error blocks every land in cloc.

Add frob release adopt VERSION: record an existing tag as a release cut without touching git or the remote. It resolves the tag(s) the configured pattern and products name for VERSION, verifies each exists and points at a commit (annotated or lightweight), and appends the same cut event release cut writes (version, commit, tag names and oids) marked adopted=true with the actor and an optional --reason; the milestone, if one exists for that version, moves to released, otherwise the cut is recorded without one. Idempotent (a repeat returns already). REL001 then treats an adopted cut like any cut. REL001's remedy names adopt first ("record it with frob release adopt X"), deletion only as the alternative. Update releases.md (verbs table) and the runbook.
