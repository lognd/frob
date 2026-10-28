+++
id = "01M1WJMD47JFMT0AQKF2EAXR0A"
title = "extend the PII-structural gate to model the message/extra split inside a log record"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M1WJMD2FWKPS1J7MPF18KDVY"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-28T12:55:41Z"
aliases = ["T-4231"]
labels = ["v1-cluster:B4", "triage:accepted", "no-story"]
scope = ["src/frob/gates/_pii_structural"]
+++

Consumer F-373/P9 (T-4175): a redaction test passes secrets in the log message, which is the surface the filter handles; the PII gate is structural (it knows which nodes/files carry which PII classes) and does not model the message/extra split inside a log record, so a secret passed via extra= would be invisible to both the filter and the gate. Fixture-testable: YES, frob's own PII-structural gate and its own logging module.

no-story: internal engineering task in src/frob; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
