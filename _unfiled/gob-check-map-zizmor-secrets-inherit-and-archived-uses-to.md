+++
id = "01M5KYF5Z489MSRNAX1JCTEHPQ"
title = "gob-check: map zizmor secrets-inherit and archived-uses to CI013 and CI015, actionlint to grimble CI014"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-23T08:36:33Z"
updated = "2026-10-23T08:36:33Z"
scope = ["crates/gob-check/src/tool_parse.rs", "crates/gob-check/src/rules.rs", "docs/reference/tool-stages.md"]
+++

found while working 01M5F010V5GV0B7KJ7M5QQG70Q: grimble-ci now declares CI013 to CI016 natively; gob-check declares only CI014 and the tool stage has no mapping for zizmor secrets-inherit (CI013) or archived-uses (CI015).
