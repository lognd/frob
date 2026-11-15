+++
id = "01M7EXT152EKW9V8Q9Q3QWZ838"
title = "gob-diagnostics: SARIF 2.1.0 emit renderer with partialFingerprints, suppressions and baselineState"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-15T06:20:11Z"
updated = "2026-11-15T06:20:12Z"
idempotency_key = "static-research-k2"
labels = ["no-story"]

[[acceptance]]
text = "frob check can emit valid SARIF 2.1.0 (--format sarif or equivalent) validated against a schema-shape test"
bound = false

[[acceptance]]
text = "Each result carries a stable partialFingerprints entry equal to the frob fingerprint, and excepted findings carry suppressions with justification"
bound = false

[[acceptance]]
text = "Docs list the SARIF output and its field mapping"
bound = false
+++

Source: /home/logan/projects/frob-research-static-analysis.md section 6 item 2, section 3. Rationale: frob ingests SARIF (crates/gob-check/src/sarif.rs) but no emit path was found (report flags this as verify: grep gob-diagnostics, which has command/envelope/text/record modules and no sarif module at HEAD). Remedy: add a SARIF renderer: ruleId, level, locations, partialFingerprints from the frob finding fingerprint (versioned key), suppressions[] from frob exceptions (frob:accept/defer), baselineState from the land ratchet. Enables GitHub code scanning and any SARIF viewer. Note GitHub limits (25k results/run, 10MB gz) are [M]: verify first. Crates/files: crates/gob-diagnostics/src (new renderer), crates/frob output format selection.
