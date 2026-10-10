+++
id = "01M4M2PCXZDTQRDNG0Z5SP0J59"
title = "nextest ci profile: gob-check ui_product (trybuild) hits the 120 s hang guard on Windows; add it to the reviewed override list with the trybuild test group"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 1
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-10T23:34:42Z"
updated = "2026-10-10T23:39:49Z"
scope = [".config/nextest.toml"]

[[acceptance]]
text = "the ci profile gives gob-check ui_product the same reviewed 300 s allowance as the other trybuild binaries and runs it in the trybuild test group, covered by the nextest config test"
bound = true
+++

CI Windows nextest: TIMEOUT [120.076s] gob-check::ui_product, with gob-macros::ui SLOW at 90 s. The override list in .config/nextest.toml covers gob-macros ui and ui_rule_attr only. ui_product is a trybuild compile-fail test that cold-builds like them.
