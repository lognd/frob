+++
id = "01M3ZX7F57JCT6CZXY5VS9RHTR"
title = "Executor skips files and subtrees lacking the plan's prefilter kinds"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:21Z"
updated = "2026-10-03T03:34:21Z"
idempotency_key = "m2-exec-prefilter"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-plan/src/exec/prefilter.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7EQ5NARR4Z2SAY4H23AQ"

[[links]]
kind = "blocked-by"
target = "01M3ZX7ETPH5Z6K2VJ64K5XTMX"

[[acceptance]]
text = "Given a plan requiring a directive kind and a file with none, when executed, then the file is skipped and counted as skipped, not as clean-by-examination"
bound = false

[[acceptance]]
text = "Given a file containing the kind, when executed, then results equal those of an unfiltered run"
bound = false
+++

Implements plugins.md section 6.2.

Prefilter by node kind is the main reason host-executed rules stay close to handwritten Rust.
