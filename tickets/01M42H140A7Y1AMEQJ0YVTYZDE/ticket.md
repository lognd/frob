+++
id = "01M42H140A7Y1AMEQJ0YVTYZDE"
title = "frob init mentions the private-term privacy.toml locations"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-04T03:58:53Z"
updated = "2026-10-04T04:11:59Z"
scope = ["crates/frob/src/init.rs", "docs/design/architecture.md", "docs/reference/rules/TICK005.md", "crates/frob-ledger/src/rules.rs"]

[[acceptance]]
text = "frob init output names the user and git-common-dir privacy.toml paths and writes neither"
bound = false

[[acceptance]]
text = "Given the TICK005 rule page and frob doctor, when a user reads them, then they show the privacy.toml format ([[rule]] with pattern, replace, regex, case_sensitive) and both file locations"
bound = false
+++

follow-up from ~2GXRW72: call frob_ledger::redact::RuleSet::mention_local_files(repo.common_dir()) in init (as doctor does), then drop the 'frob init to follow' note in architecture.md section 6
