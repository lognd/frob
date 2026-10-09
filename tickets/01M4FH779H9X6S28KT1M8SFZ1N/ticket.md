+++
id = "01M4FH779H9X6S28KT1M8SFZ1N"
title = "crunk.toml accepts unknown tables and keys (a [bogus] table, v1 [layers]) although the config contract says unknown keys are errors"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T05:12:21Z"
updated = "2026-10-09T20:57:19Z"
labels = ["adoption:logand-app"]
scope = ["changelog.d/**", "crates/crunk-check/src/product.rs", "crates/crunk-spec/src/error.rs", "crates/crunk-spec/src/load.rs", "crates/crunk-check/tests/spec_errors.rs", "crates/crunk-spec/tests/spec.rs"]

[[acceptance]]
text = "Given crunk.toml with a [bogus] table or the v1 [layers] table, when crunk check or frob check runs, then the load fails with the unknown-key error naming the table, exactly as frob.toml does"
bound = false

[[acceptance]]
text = "Given a known crunk.toml table (e.g. [layers]) containing keys outside its v2 schema (v1-shaped content), when crunk check or frob check runs, then the load fails naming each unknown key, the same as an unknown table"
bound = false
+++

logand.app-v2 F-541.
