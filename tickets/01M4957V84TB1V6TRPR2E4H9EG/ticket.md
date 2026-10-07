+++
id = "01M4957V84TB1V6TRPR2E4H9EG"
title = "Load-sensitive tests break whole-workspace evidence on a busy host: frob-pm corpus, gob-ir deep stack, gob-macros trybuild"
type = "bug"
category = "in-progress"
priority = "medium"
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T17:47:32Z"
updated = "2026-10-07T02:17:40Z"
scope = [".config/nextest.toml", "crates/frob-pm/tests/**", "crates/gob-ir/tests/**", "crates/gob-macros/tests/**"]

[[acceptance]]
text = "each named test is under its timeout at load average twice the core count, or has a reviewed override with the measured reason"
bound = true

[[acceptance]]
text = "the gob-macros::ui failure under load is explained and fixed"
bound = true
+++

Measured 2026-10-06 on this host at load ~20 with another agent building: whole-workspace evidence for ~HQ6B02X failed with frob-pm::corpus mdtest_corpus TIMEOUT 120 s, gob-ir::deep a_million_levels_deep_on_a_default_stack_is_total TIMEOUT 132 s and gob-macros::ui FAIL after 109 s, while the same tree had passed the nextest step of cargo dev ci minutes earlier. Each costs an evidence run (also seen for gob-macros::ui_rule_attr and gob-ir deep earlier the same day). Measure each test cold and under load, then either make it cheaper (smaller corpus per case, a lower depth with the same stack property, shared trybuild warm target) or give it a reviewed nextest override with the measured reason; find out why gob-macros::ui FAILs rather than times out under load.
