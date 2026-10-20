+++
id = "01M47QTW8CA2FD3BQTH2GG2KXR"
title = "Inline parser tests: test_ok and test_err blocks in parser source, extracted by cargo dev gen"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T04:34:01Z"
updated = "2026-10-06T04:34:01Z"
scope = ["crates/gob-dev/**", "crates/gob-plan/**", "crates/grimble-model/**", "crates/gob-directives/**", "crates/crunk-spec/**"]

[[acceptance]]
text = "at least five test_ok and five test_err blocks per parser"
bound = false

[[acceptance]]
text = "a stale extraction fails cargo dev gen --check"
bound = false
+++

build-test-ci.md section 6, ruff_python_parser and rust-analyzer. Parsers of GRL (gob-plan), .grmb (grimble-model), directives (gob-directives) and crunk.toml (crunk-spec) carry comment blocks marked test_ok NAME or test_err NAME; cargo dev gen extracts them to resources/inline/ok and err; a test snapshots the tree and errors of each; GEN001 keeps extraction current.
