+++
id = "01M4XJMM949EHC6X13TYJPYE5V"
title = "GRL executor/runner: kinds link and directive, edge relations calls and resolves to, multi-file and config and diff/lease inputs, language-less examples"
type = "task"
category = "in-progress"
priority = "medium"
points = 8
reporter = "lognd"
created = "2026-10-14T16:06:31Z"
updated = "2026-10-14T16:11:25Z"
labels = ["area:grl"]
scope = ["crates/gob-plan/src/exec/**", "crates/gob-plan/src/examples/**", "crates/gob-plan/src/lower/convert.rs"]

[[acceptance]]
text = "Given the TODO001 rule, when its examples run through run_example, then all pass (kind directive is supported)"
bound = false

[[acceptance]]
text = "Given the COV001 and NEAT013 rules, when their examples run, then the calls and resolves to edge relations are supplied and the examples pass"
bound = false

[[acceptance]]
text = "Given the SCOPE001 rule (lang -), when its language-less examples with diff, lease and config inputs run, then they pass"
bound = false
+++

found while working ~0HC06TD. The six fixtures lower but the executor/runner rejects: kind link (DOC002), kind directive (TODO001), edge relations calls (COV001) and resolves to (NEAT013), example inputs file/config/diff/lease (DOC002, INV002, SCOPE001), and lang - examples (SCOPE001).
