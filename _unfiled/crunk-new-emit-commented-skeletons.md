+++
id = "01M7EXTFTEW147EGH3G7P8JJDT"
title = "crunk new: emit commented skeletons"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:26Z"
updated = "2026-11-15T06:20:26Z"
idempotency_key = "crunkplan-763ff294e2dc"
labels = ["no-story"]

[[acceptance]]
text = "crunk new screen output passes crunk check"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding M11.
Evidence: crunk new emits bare files
Remedy: emit commented skeletons that pass check
Crates/files: crates/crunk new verb
Verify against HEAD first; the audit ran on a stale binary.
