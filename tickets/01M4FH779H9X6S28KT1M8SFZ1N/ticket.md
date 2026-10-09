+++
id = "01M4FH779H9X6S28KT1M8SFZ1N"
title = "crunk.toml accepts unknown tables and keys (a [bogus] table, v1 [layers]) although the config contract says unknown keys are errors"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T05:12:21Z"
updated = "2026-10-09T05:12:21Z"
labels = ["adoption:logand-app"]
scope = ["crates/crunk*/**", "crates/gob-config/**", "changelog.d/**"]

[[acceptance]]
text = "Given crunk.toml with a [bogus] table or the v1 [layers] table, when crunk check or frob check runs, then the load fails with the unknown-key error naming the table, exactly as frob.toml does"
bound = false
+++

logand.app-v2 F-541.
