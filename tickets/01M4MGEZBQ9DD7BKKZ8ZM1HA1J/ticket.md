+++
id = "01M4MGEZBQ9DD7BKKZ8ZM1HA1J"
title = "Test executables: about 570 integration-test binaries at 24 MB each (12 GB) make a full test build unaffordable; consolidate to one test binary per crate or link dynamically"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-11T03:35:19Z"
updated = "2026-10-18T04:45:08Z"
scope = ["Cargo.toml", "crates/gob-dev/**", "docs/**"]

[[acceptance]]
text = "a full workspace test build leaves under 3 GB of test executables, measured by a script in cargo dev that sums the files, and CI still passes"
bound = false
+++

found while draining tickets: a core-crate change links about 570 test executables averaging 24 MB stripped, 12 GB in total, which does not fit a 25 GB disk and serialized all workers behind one build lock. Options: fold crates/*/tests/*.rs into one tests/main.rs per crate (the standard remedy), prefer-dynamic for test profiles, or a shared test harness binary. Measure before and after.
