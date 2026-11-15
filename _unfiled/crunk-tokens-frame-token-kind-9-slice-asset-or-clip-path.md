+++
id = "01M7EXWNMZVTG99EX1ZQHXNDXR"
title = "crunk tokens: frame token kind (9-slice asset or clip-path corner cut)"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M7ETB6DKRHKAHRBA2NCGNQTB"
reporter = "lognd"
created = "2026-11-15T06:21:38Z"
updated = "2026-11-15T06:21:38Z"
idempotency_key = "crunkplan-66590d1da7f1"
labels = ["no-story"]

[[acceptance]]
text = "a 9-slice frame exports to css border-image and USS slice properties (snapshot)"
bound = false
+++

Source: ~/projects/frob-research-ui.md, section T3.
Remedy: add TokenKind::Frame; css border-image/mask and USS -unity-slice-* export
Crates/files: crates/crunk-tokens, crates/crunk-export
Keep any new heuristic advisory and dated; a clean run means no known defect, not quality.
