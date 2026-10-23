+++
id = "01M1T07J3YQPFGZ1XYZZTRGB98"
title = "r14: --config flag for borrowed specs (A-070)"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-09-06T00:00:03Z"
aliases = ["crunk:T-0126"]
labels = ["component:crunk", "source:crunk"]
scope = ["docs/design/01-customer-requirements.md", "docs/design/02-specification.md", "docs/design/subsystems/shell.md"]

[[acceptance]]
text = "given the three docs, when read, then the --config semantics, the no-discovery decision, and CT/E2E ids are stated"
bound = true
+++

A sibling branch predating the crunk adoption cannot run check because the spec file lives on another branch. Design: an explicit global --config PATH flag separating spec location from project root (root stays cwd, paths resolve against root as ever); deliberately NO upward discovery -- silently picking a config up the tree is magic that misfires. load_spec_file already provides the seam.
