+++
id = "01M5XCZ1C4P58PFPRCH880G1HE"
title = "Post-launch artifacts: design/metrics (HEART) and experiments with PROC rules"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CXSAG0YPF18FX3KAPVX45C"
reporter = "lognd"
created = "2026-10-27T00:43:02Z"
updated = "2026-10-27T00:43:07Z"
labels = ["area:crunk"]
scope = ["crates/crunk-spec/src/metrics.rs, crates/crunk-rules/src/proc/**, crates/crunk-rules/tests/proc_metrics.rs"]

[[links]]
kind = "blocked-by"
target = "01M5XCYCP797Z6M8WPBW7FAD5W"

[[acceptance]]
text = "Given a flow step with no defined analytics event, when checked, then a PROC finding names it; given an experiment variant not declared as a component variant, then it fires; given an experiment with no guardrail metric, then it fires; given an experiment older than its max age, then a stale finding fires. Edge cases: a metric referencing an unknown goal is a dangling finding; duplicate metric ids refused; phase below live skips these rules (see the phase ticket); empty dirs silent"
bound = false
+++

Design crunk.md section 8 post-launch row.
