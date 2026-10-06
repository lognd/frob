+++
id = "01M40C92S9KDSA59ZSGYPRBJPF"
title = "gob-check: rule applicability carries a reason that is reported and counted, not only logged"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T07:57:23Z"
updated = "2026-10-06T13:56:15Z"
idempotency_key = "m2-applicable-reason"
labels = ["milestone:2"]
scope = ["crates/gob-check/**", "crates/frob-check/**", "crates/grimble-check/**", "crates/frob-pm/src/rules/**"]

[[links]]
kind = "superseded-by"
target = "01M48R00MZS92F2KY5T60SBHYV"

[[acceptance]]
text = "Given a rule that is NotApplicable with a reason, when frob check --json runs, then the reason appears once in the not-applicable list and the count, and no finding is produced"
bound = false
+++

Found on ~SV1E7PS: the applicable hook returns bool, so a NotApplicable rule's reason (for example PM034: no milestone objects in this repository) appears only in the info log. universal-model.md 4 says NotApplicable never produces a finding but is counted once per language in the fidelity report, and grimble already lists not-applicable rules with reasons (~S3AFCP4, fidelity.not_applicable_rules). Change the hook to return Applicability { Applicable, NotApplicable(reason) } across gob-check, frob-check and grimble-check, report each NotApplicable rule once with its reason in the check JSON (a summary count plus the list) and in --text under a quiet summary line, and convert existing bool hooks. No change in exit status.
