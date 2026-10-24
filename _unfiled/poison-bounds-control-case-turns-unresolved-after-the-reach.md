+++
id = "01M5P5BX83VZV2GJWS180A1QKV"
title = "poison_bounds control case turns Unresolved after the Reach poison fix"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-24T05:15:35Z"
updated = "2026-10-24T05:42:56Z"
scope = ["crates/frob-tests/**", "crates/gob-ir/**"]

[[acceptance]]
text = "poison_bounds::pc_and_pn_bounds_never_fold_poison_into_a_pass passes with the G2WTCQG Reach-under-poison fix kept"
bound = true
+++

CI on 5606166d4d: control case expected Clean, got Unresolved EdgeMay. Decide whether the test expectation or the taint rule is wrong; keep a_definite_reach_under_poison_never_yields_clean passing.
