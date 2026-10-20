+++
id = "01M2C10QBJXB647M8XYJHJ6HKH"
title = "REF002: docs/design/macos-portability.md has only one inbound reference"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-13T00:00:00Z"
updated = "2026-10-04T21:07:51Z"
aliases = ["T-4466"]
labels = ["milestone:0.544.0", "v1-cluster:F1"]
scope = ["docs/design/macos-portability.md"]
+++

MEASURED via frob check --ticket T-4463 (repo-wide REF002 gate, unrelated to T-4463's own scope): docs/design/macos-portability.md has exactly one inbound reference (docs/index.md) -- REF002 wants a second consumer/declaration or a frob:waive. Pre-existing since at least T-3488/T-3586; not something T-4463 touches. File a second consumer/anchor or waive with reason.
