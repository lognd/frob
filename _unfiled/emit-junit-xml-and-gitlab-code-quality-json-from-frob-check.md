+++
id = "01M7EXV9C7F2G3WJ50VTMPRGZ4"
title = "Emit JUnit XML and GitLab code-quality JSON from frob check and frob test"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:20:52Z"
updated = "2026-11-15T06:20:52Z"
idempotency_key = "static-research-k11"
labels = ["no-story"]
+++

Source: /home/logan/projects/frob-research-static-analysis.md section 6 item 10, section 3. Rationale: CI UIs and GitLab MR widgets consume JUnit and the CodeClimate-shaped code-quality report. The report says gob-diagnostics should carry these renderers and that none were verified beyond the plan: confirm first (crates/gob-diagnostics/src has no junit/gitlab module at HEAD). Remedy: two output renderers fed by the same finding/test records as the SARIF renderer. Crates/files: crates/gob-diagnostics/src, crates/frob output selection.
