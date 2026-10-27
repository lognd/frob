+++
id = "01M1QDTV2NEG2RS2DV3DJT3QM7"
title = "r8: T-0146 re-trial findings A-030..A-032"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:37Z"
aliases = ["crunk:T-0085"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["docs/design/*.md", "docs/design/subsystems/*.md"]

[[acceptance]]
text = "given A-030..A-032, when the design tree is read, then each maps to a contract change"
bound = true
+++

Re-trial findings: A-030 generated-file path bases are inconsistent and silently orphan stale copies; A-031 explain's uses index misses JSX/Tailwind sites entirely (would have caused real deletions); A-032 preview has no force-color escape hatch. Design: path-base RULE stated ([project] keys are css_root-relative, every other *_file key is project-root-relative -- compat forbids rebasing either) plus an orphan-copy warning; explain sites and utilities fed from the same JSX ingest check uses; --color flag on preview/diff.
