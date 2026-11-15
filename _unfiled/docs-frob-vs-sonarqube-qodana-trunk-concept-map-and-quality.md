+++
id = "01M7EXVWN3M8AJVA8V7869CJC2"
title = "Docs: frob vs SonarQube/Qodana/Trunk concept map, and quality/attribute tags on rule pages"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:21:12Z"
updated = "2026-11-15T06:21:12Z"
idempotency_key = "static-research-k16"
labels = ["no-story"]

[[acceptance]]
text = "A docs page maps at least ratchet, pack, exceptions and fingerprints to their SonarQube, Qodana and Trunk counterparts"
bound = false

[[acceptance]]
text = "Rule frontmatter accepts quality and attribute and generated docs pass gob-dev gen all --check"
bound = false
+++

Source: /home/logan/projects/frob-research-static-analysis.md section 6 item 14, sections 1.1 to 1.5. Rationale: Sonar's clean-as-you-code equals the land ratchet, quality profile equals a pack, accepted issue equals frob:accept/defer with expiry, issue identity equals fingerprint. Sonar rows are [F]; Qodana/Trunk rows are [M], verify first. Remedy: one docs page with the mapping, and optional quality and attribute fields in rule-page frontmatter so rule listings can filter. Crates/files: docs/guides (new page), rule-page frontmatter schema and generator.
