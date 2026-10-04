+++
id = "01M1WJMD45JZE1BZYCXTTQYWR4"
title = "runbook fenced shell commands: a doc-adjacent directive naming the execution container, checkable by lint or dry-run"
type = "task"
category = "todo"
priority = "low"
parent = "01M1WJMD2FWKPS1J7MPF18KDVY"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-04T22:22:23Z"
aliases = ["T-4229"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/gates"]
+++

Consumer F-373/P5 (T-4175): a unit test exercises a runbook script under a dry-run env var, but no test executes, parses, or lints the runbook's own documented fenced commands, and frob's doc gates check anchors and drift, not whether a documented shell command would actually run. Mark runbook code fences with a directive naming the container they run in, and lint/dry-run against it. Not fixture-testable in frob's own tree: no runbooks/containers exist here.
