+++
id = "01M7EXSBHBB6H9BJCHG3DXT5FD"
title = "gob-check: generic SARIF stage without id_map, auto-namespaced ext.<tool>.<ruleId>"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:19:49Z"
updated = "2026-11-15T06:19:49Z"
idempotency_key = "static-research-k1"
labels = ["no-story"]
+++

Source: /home/logan/projects/frob-research-static-analysis.md section 6 item 1 and section 4.3 step 2. Rationale: today parser=sarif ids come from the per-stage id_map (crates/gob-check/src/config.rs id_map, tool_parse.rs default_id_map, sarif.rs parse_sarif), so an unknown SARIF tool needs config before it can be dropped in. Remedy: when parser=sarif has no id_map entry for a result, map it to rule ext.<tool>.<ruleId> (tool from runs[].tool.driver.name, lowercased), severity from SARIF level, overridable via [rules."ext.x.y"] and dismissable. Fingerprints must use SARIF partialFingerprints when present. Crates/files: crates/gob-check/src/sarif.rs, tool_parse.rs, config.rs, docs/design tool-stages doc. Evidence grade: report [R] for current code, the catalogue of SARIF tools is [M].
