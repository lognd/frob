+++
id = "01M1QDTYRVYX3GN7QWWXNRFKH7"
title = "NARR001 (narrative-block placement) burn-down: 156 unwaived findings"
type = "bug"
category = "triage"
priority = "medium"
reporter = "agent"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:00Z"
aliases = ["T-3867"]
labels = ["milestone:1.0.0", "v1-cluster:F1"]
+++

T-3844 burn-down: this rule/cluster (NARR001) carried 156 unwaived warning-level findings on the 2026-09-05 full unscoped 'frob check --no-cache' baseline measured for T-3844 (see that ticket's body for the full histogram). It is intentionally NOT promoted to error by T-3844 -- promoting a rule that still fires reds the build for everyone. This ticket's job: drive the live unwaived finding count for NARR001 to zero (real fixes and/or reasoned frob:waive entries), then promote NARR001 from warn to error in frob.toml's [gates.severity] T-1002 managed zone as a follow-up to this same campaign.
