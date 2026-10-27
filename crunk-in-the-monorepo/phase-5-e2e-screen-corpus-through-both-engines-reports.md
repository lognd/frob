+++
id = "01M5XCXVVHQ2SMQFAJVWPZ2BDG"
title = "Phase 5 e2e: screen corpus through both engines reports parity, VIS and axe findings and above-tier lints as not run"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXRV40WWJQKHWJJBKJT1HZ"
reporter = "lognd"
created = "2026-10-27T00:42:24Z"
updated = "2026-10-27T00:42:30Z"
labels = ["area:crunk"]
scope = ["crates/crunk/tests/e2e_render_tiers.rs, crates/crunk/tests/fixtures/render_corpus/**"]

[[links]]
kind = "blocked-by"
target = "01M4CXRWBYR6P0WFRW5GBBJGEY"

[[links]]
kind = "blocked-by"
target = "01M5XCXV02ZVYV71DFY08R5Y3H"

[[acceptance]]
text = "Given the corpus, when both engines render in the optional playwright job, then parity, VIS and axe findings appear in one report; given playwright absent, then those findings are not run, not green, and the job is skipped with a notice"
bound = false
+++

Epic acceptance for phase 5. Test-only.
