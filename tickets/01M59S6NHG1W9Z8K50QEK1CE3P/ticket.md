+++
id = "01M59S6NHG1W9Z8K50QEK1CE3P"
title = "docs(mirror): document fields.rs ownership guard in mirror.md 3.4/3.6"
type = "task"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-19T09:52:07Z"
updated = "2026-10-19T13:22:19Z"
idempotency_key = "mirror-fields-docs"
+++

Landed with ~N1E4FA4 without its docs because ~GXM4RK4 holds docs/design/mirror.md. Add a short subsection under 3.4 and 3.6 covering FieldsConfig, FieldOwnership::load/authorize, plan_writes, plan_project_writes; WriteOp only built via authorize; only frob: labels and project field status writable.
