+++
id = "01M1QDTYS567KHB84Q076W9AYY"
title = "misc lint/ref hygiene cluster (unused-ignore-comment/possibly-missing-submodule/NEGEXIST001/REF003) burn-down: 11 unwaived findings"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "agent"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-04T21:07:42Z"
aliases = ["T-3877"]
labels = ["milestone:0.541.0", "v1-cluster:F1"]
+++

T-3844 burn-down: this rule/cluster (unused-ignore-comment,possibly-missing-submodule,NEGEXIST001,REF003) carried 11 unwaived warning-level findings on the 2026-09-05 full unscoped 'frob check --no-cache' baseline measured for T-3844 (see that ticket's body for the full histogram). It is intentionally NOT promoted to error by T-3844 -- promoting a rule that still fires reds the build for everyone. This ticket's job: drive the live unwaived finding count for unused-ignore-comment,possibly-missing-submodule,NEGEXIST001,REF003 to zero (real fixes and/or reasoned frob:waive entries), then promote unused-ignore-comment,possibly-missing-submodule,NEGEXIST001,REF003 from warn to error in frob.toml's [gates.severity] T-1002 managed zone as a follow-up to this same campaign.
