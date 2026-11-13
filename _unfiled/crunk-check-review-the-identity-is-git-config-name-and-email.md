+++
id = "01M7ABZSS4WQ3R08CWQMS2PFJT"
title = "crunk-check review::the_identity_is_git_config_name_and_email_or_unknown fails when ambient git config has an email"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-13T11:51:48Z"
updated = "2026-11-13T12:23:02Z"
idempotency_key = "identity-test-ambient-git"
scope = ["crates/crunk-check/tests/it/review.rs"]

[[acceptance]]
text = "Given an ambient git config with a user.email, when the identity test runs, then it passes with name-only then name+email results"
bound = true
+++
