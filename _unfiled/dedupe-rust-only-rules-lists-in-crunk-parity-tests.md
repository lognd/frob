+++
id = "01M5P15B93BTSR4HSWS6C5QDQC"
title = "Dedupe RUST_ONLY_RULES lists in crunk parity tests"
type = "chore"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-24T04:02:05Z"
updated = "2026-11-11T03:25:55Z"
scope = ["crates/crunk/tests/**", "changelog.d/**"]

[[acceptance]]
text = "RUST_ONLY_RULES is defined once in crates/crunk/tests/common/mod.rs and both parity tests use it"
bound = true
+++

found while working ~MJZYWH9: crates/crunk/tests/parity/compare.rs and crates/crunk/tests/query_parity.rs carry duplicated RUST_ONLY_RULES lists; extract one shared constant.
