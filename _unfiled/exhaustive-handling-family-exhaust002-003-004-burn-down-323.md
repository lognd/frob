+++
id = "01M1QDTYRNF19C5RZJQWX90JBF"
title = "exhaustive-handling family (EXHAUST002/003/004) burn-down: 323 unwaived findings"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "agent"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:02Z"
aliases = ["T-3861"]
labels = ["milestone:0.541.0"]
scope = ["scripts/fleet_status.py"]
+++

T-3844 burn-down: this rule/cluster (EXHAUST002,EXHAUST003,EXHAUST004) carried 323 unwaived warning-level findings on the 2026-09-05 full unscoped 'frob check --no-cache' baseline measured for T-3844 (see that ticket's body for the full histogram). It is intentionally NOT promoted to error by T-3844 -- promoting a rule that still fires reds the build for everyone. This ticket's job: drive the live unwaived finding count for EXHAUST002,EXHAUST003,EXHAUST004 to zero (real fixes and/or reasoned frob:waive entries), then promote EXHAUST002,EXHAUST003,EXHAUST004 from warn to error in frob.toml's [gates.severity] T-1002 managed zone as a follow-up to this same campaign.

frob:no-behavior-change reason="This ticket's diff-touched production file, scripts/fleet_status.py, receives ONLY frob:waive EXHAUST003 comment additions across this leaf -- no executable code line changed (verified: every added line in the diff is a #-prefixed comment). Pure lint-metadata/waiver-comment edit, no runtime behavior differs; BUG002/mutation-kill evidence structurally cannot apply the way it does to a code-path bug fix, per this same T-1616 precedent used by other EXHAUST/WAIVE burn-down leaves."
