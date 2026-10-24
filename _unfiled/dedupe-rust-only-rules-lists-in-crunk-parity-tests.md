+++
id = "01M5P15B93BTSR4HSWS6C5QDQC"
title = "Dedupe RUST_ONLY_RULES lists in crunk parity tests"
type = "chore"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-24T04:02:05Z"
updated = "2026-10-24T04:02:05Z"
scope = ["crates/crunk/tests/**"]
+++

found while working ~MJZYWH9: crates/crunk/tests/parity/compare.rs and crates/crunk/tests/query_parity.rs carry duplicated RUST_ONLY_RULES lists; extract one shared constant.
