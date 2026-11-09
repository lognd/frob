+++
id = "01M6Z2SXMWBKP1SS1NPE0MT1GQ"
title = "crunk-rules: RESP001 reads crunk-layout solver output at each declared breakpoint"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-09T02:39:40Z"
updated = "2026-11-09T03:46:11Z"
scope = ["crates/crunk-rules/src/rules/resp001.*", "crates/crunk-layout/tests/corpus.rs", "crates/crunk-layout/src/findings.rs", "crates/crunk-rules/src/scene_docs.rs"]

[[acceptance]]
text = "RESP001 fires from crunk-layout solves at each breakpoint width"
bound = false

[[acceptance]]
text = "corpus test local root-width code removed"
bound = false
+++

Found while working ~SXJJYWH. RESP001 still checks that a scene.json viewport equals each [breakpoints] width. HTML scenes carry no viewport, so the rule needs redefining: solve each scene.html at every declared breakpoint (SceneDocFile::solve is fixed at 1280) and fire when the root is wider than the viewport, which is what the corpus test computes locally as 'RESP001'. Then delete that local root-width code from crates/crunk-layout/tests/corpus.rs and convert resp001.md examples to HTML.
