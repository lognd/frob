+++
id = "01M4P0SXNWX5H7J2EMR01D50YZ"
title = "dup baseline: baseline file so error-by-default does not fail existing clones"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4P0SQC82NJ7DV5BC3CAR5Y4"
reporter = "lognd"
created = "2026-10-11T17:40:09Z"
updated = "2026-11-05T16:58:30Z"
labels = ["no-story", "good-first"]
scope = ["crates/frob-check/**"]

[[acceptance]]
text = "Given existing clone clusters, when frob dup baseline runs, then baselined clones do not fail and each entry carries a reason and owner ticket"
bound = false
+++

Add a dup baseline file so error-by-default does not fail existing clones.

## Start here

Look at the existing baseline handling in crates/frob-check and mirror it for dup clusters.
