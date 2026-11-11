+++
id = "01M69111SMC07EPRTKFSF4719D"
title = "crunk boundary test fails: gob-cli depends on frob-present"
type = "bug"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-31T13:05:19Z"
updated = "2026-11-11T15:43:32Z"
scope = ["crates/gob-cli/Cargo.toml", "crates/crunk/tests/boundary.rs"]

[[acceptance]]
text = "crunk::boundary no_frob_crate_is_a_direct_or_transitive_dependency_of_a_crunk_crate passes"
bound = true
+++

found while working ~Z03B67Y: fails on experimental independent of that change; gob-cli -> frob-present.
