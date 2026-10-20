+++
id = "01M4PZTQGGPR4K03T4W0AHKXWC"
title = "GRL lowerer gaps block acceptance corpus A: knobs, is, 3-segment paths, globs, vocab relation"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-12T02:42:21Z"
updated = "2026-10-15T23:44:37Z"
scope = ["crates/gob-plan/src/lower/**", "crates/gob-plan/src/examples/corpus_tests.rs"]

[[acceptance]]
text = "Given the six section 12 rules TODO001 DOC002 COV001 INV002 SCOPE001 NEAT013, when run_example runs each example, then none fails with a cannot-lower error"
bound = true
+++

Found on ~0HC06TD: the six rules parse but run_example fails: cannot lower a knob yet; cannot lower is yet; cannot lower a path of more than two segments yet; cannot lower a glob that is not a literal yet; unknown side relation vocab(sources). Fixtures are verbatim from grl-spec.md section 12.
