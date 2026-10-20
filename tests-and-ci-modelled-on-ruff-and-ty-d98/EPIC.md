+++
id = "01M47QTS14TAZQ67NN2M9NHDJP"
title = "Tests and CI modelled on ruff and ty (D98)"
type = "epic"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-10-06T04:33:58Z"
updated = "2026-10-06T04:33:58Z"

[[acceptance]]
text = "Every child closed or dropped with a reason"
bound = false

[[acceptance]]
text = "cargo dev ci --list shows the snapshots, deny, shear, typos, msrv and fuzz-build steps"
bound = false
+++

Implements docs/design/build-test-ci.md section 6 (D98, owner request 2026-10-06). Every practice is a cargo dev ci step or a nextest test so local, goway and GitHub runs are the same.
