+++
id = "01M7EXR3KBM1TYHCD45A3PQ5F4"
title = "file-size ratchet rule"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:19:08Z"
updated = "2026-11-15T06:19:08Z"
labels = ["no-story"]

[[acceptance]]
text = "Growing a baselined file is a finding (test)"
bound = false
+++

Source: frob-audit2-repo.md M7/F9. Evidence: land.rs and gob-symbols rust.rs oversized. Remedy: rule with per-file baseline. Files: rule crate, baseline.
