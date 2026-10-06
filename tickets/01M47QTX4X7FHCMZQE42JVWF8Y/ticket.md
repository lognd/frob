+++
id = "01M47QTX4X7FHCMZQE42JVWF8Y"
title = "Formatter and printer idempotence: grimble fmt and the GRL printer"
type = "story"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T04:34:02Z"
updated = "2026-10-06T07:25:34Z"
scope = ["crates/grimble-model/**"]

[[acceptance]]
text = "grimble fmt: format(format(x)) equals format(x) and parse(format(x)) preserves U over every .grmb fixture"
bound = true

[[acceptance]]
text = "a .grmb proptest generator with a self-test where a broken printer fails with a shrunk minimal example"
bound = true
+++

build-test-ci.md section 6, ruff_python_formatter stability checks. format(format(x)) equals format(x) and parse(print(t)) equals t over every .grmb and GRL fixture and a proptest generator.
