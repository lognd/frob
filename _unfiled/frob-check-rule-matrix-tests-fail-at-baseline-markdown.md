+++
id = "01M5NHCSZB0543SWHP6E2ACM70"
title = "frob-check rule_matrix tests fail at baseline (markdown COV001/DOC001 cells, DOC001 island garbage probe)"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-23T23:26:32Z"
updated = "2026-10-23T23:26:32Z"
scope = ["crates/frob-check/tests/**"]

[[acceptance]]
text = "Given the frob-check rule_matrix tests, when they run, then every_universal_frob_rule_fills_the_matrix and garbage_input_never_panics_and_stays_unresolved pass"
bound = false
+++

Found while working 01M5NFNVB515TW2DH23FSH0MZS. Failing at baseline: COV001/DOC001 markdown cell expects clean but the capability matrix derives notapplicable; DOC001 island garbage probe reports neither Unresolved nor NotApplicable.
