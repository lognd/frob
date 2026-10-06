+++
id = "01M47QTX4X7FHCMZQE42JVWF8Y"
title = "Formatter and printer idempotence: grimble fmt and the GRL printer"
type = "story"
category = "todo"
priority = "medium"
points = 3
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T04:34:02Z"
updated = "2026-10-06T04:34:02Z"
scope = ["crates/grimble-model/**", "crates/gob-plan/**"]

[[acceptance]]
text = "idempotence and round-trip tests over all fixtures"
bound = false

[[acceptance]]
text = "a proptest generator for each language with a shrinking failure example in a self-test"
bound = false
+++

build-test-ci.md section 6, ruff_python_formatter stability checks. format(format(x)) equals format(x) and parse(print(t)) equals t over every .grmb and GRL fixture and a proptest generator.
