+++
id = "01M4XJMM949EHC6X13TYJPYE5V"
title = "GRL executor/runner: kinds link and directive, edge relations calls and resolves to, multi-file and config and diff/lease inputs, language-less examples"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 8
reporter = "lognd"
created = "2026-10-14T16:06:31Z"
updated = "2026-10-14T16:23:17Z"
labels = ["area:grl"]
scope = ["crates/gob-plan/src/exec/**", "crates/gob-plan/src/examples/**", "crates/gob-plan/src/lower/convert.rs", "docs/design/rules.md", "changelog.d/01M4XJMM949EHC6X13TYJPYE5V.*"]

[[acceptance]]
text = "Given the TODO001 rule, when its examples run through run_example, then all pass (kind directive is supported)"
bound = true

[[acceptance]]
text = "Given COV001 and NEAT013, when examples run, then the calls and resolves to edge relations are supplied and the examples not blocked on model gaps (~M5HEN3Y, ~WNH8N7X) pass"
bound = true

[[acceptance]]
text = "Given the SCOPE001 rule (lang -), when its language-less examples with diff, lease and config inputs run, then they pass"
bound = true
+++

found while working ~0HC06TD. The six fixtures lower but the executor/runner rejects: kind link (DOC002), kind directive (TODO001), edge relations calls (COV001) and resolves to (NEAT013), example inputs file/config/diff/lease (DOC002, INV002, SCOPE001), and lang - examples (SCOPE001).
