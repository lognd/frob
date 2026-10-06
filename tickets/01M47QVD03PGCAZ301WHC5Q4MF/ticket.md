+++
id = "01M47QVD03PGCAZ301WHC5Q4MF"
title = "Change detection job: map changed paths to the CI job set"
type = "story"
category = "todo"
priority = "medium"
points = 3
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T04:34:18Z"
updated = "2026-10-06T04:34:18Z"
scope = ["crates/gob-dev/**", ".github/workflows/ci.yml"]

[[acceptance]]
text = "a docs-only diff selects only fmt, gen and check"
bound = false

[[acceptance]]
text = "a Rust diff selects the full set"
bound = false

[[acceptance]]
text = "the mapping has a unit test per class"
bound = false
+++

build-test-ci.md section 6, ruff determine_changes. A first changes step in cargo dev ci (and job in ci.yml) maps the diff to job sets: Rust, docs only, workflows, crunk node and playwright (~2H41VF1). A docs-only PR runs fmt, gen check and frob check only. The mapping is data in gob-dev with a test per class.
