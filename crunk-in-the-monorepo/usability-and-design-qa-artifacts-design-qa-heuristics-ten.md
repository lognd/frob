+++
id = "01M5XCZ14WCPMG9R6E269QRPVH"
title = "Usability and design QA artifacts: design/qa/heuristics (ten NN/g enum) and walkthrough (four questions per step)"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXSAG0YPF18FX3KAPVX45C"
reporter = "lognd"
created = "2026-10-27T00:43:02Z"
updated = "2026-10-27T00:43:02Z"
labels = ["area:crunk"]
scope = ["crates/crunk-spec/src/qa.rs, crates/crunk-rules/src/ux/qa.rs, crates/crunk-rules/tests/ux_qa.rs"]

[[acceptance]]
text = "Given a walkthrough step with any answer no, when checked, then the step fails and names which question; given a major heuristic finding with no owner reference, then a finding fires; given a screen with no heuristic coverage, then coverage fires. Edge cases: an unknown heuristic name is a schema error listing the ten; missing evidence on a finding fires; severity outside 0-4 is rejected; an empty qa dir is silent"
bound = false
+++

Design crunk.md section 8 QA row.
