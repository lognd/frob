+++
id = "01M1QDTYS0EHKZEP5JQD4MM2M4"
title = "LANG003 (per-project language conformance) burn-down: 21 unwaived findings"
type = "bug"
category = "triage"
priority = "medium"
reporter = "agent"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:00Z"
aliases = ["T-3872"]
labels = ["milestone:0.541.0", "v1-cluster:D2"]
+++

T-3844 burn-down: this rule/cluster (LANG003) carried 21 unwaived warning-level findings on the 2026-09-05 full unscoped 'frob check --no-cache' baseline measured for T-3844 (see that ticket's body for the full histogram). It is intentionally NOT promoted to error by T-3844 -- promoting a rule that still fires reds the build for everyone. This ticket's job: drive the live unwaived finding count for LANG003 to zero (real fixes and/or reasoned frob:waive entries), then promote LANG003 from warn to error in frob.toml's [gates.severity] T-1002 managed zone as a follow-up to this same campaign.
