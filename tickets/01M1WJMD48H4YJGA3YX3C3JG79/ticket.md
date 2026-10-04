+++
id = "01M1WJMD48H4YJGA3YX3C3JG79"
title = "strata: model a node's runtime-mounted artifact set; check relative import/include targets in a config file resolve within it"
type = "task"
category = "triage"
priority = "medium"
parent = "01M1WJMD174K541FJR85BEHX2T"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-09-07T00:00:00Z"
aliases = ["T-4232"]
labels = ["milestone:1.1.0", "v1-cluster:B3d"]
scope = ["src/frob/strata"]
+++

Consumer F-325/H2-1 (edge/ops round-2 sub-epic of T-4135): a config file (e.g. an edge server's include directive) references a mount path with no gate connecting the declared may fs.read grant to what a deployment's compose service actually mounts. Even without a config-file grammar, a path-set comparison between two text files frob already reads would catch this. Adjacent to T-3996 (required_file: declared surface for untracked-but-mandatory artifacts) -- distinct mechanism (mount-path resolution vs. untracked-mandatory-file declaration), cross-reference during design. Not fixture-testable in frob's own tree: no containers/mounts exist here.
