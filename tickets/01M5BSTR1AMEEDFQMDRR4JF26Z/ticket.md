+++
id = "01M5BSTR1AMEEDFQMDRR4JF26Z"
title = "TICK011: also query GitHub rulesets for ticket branch protection"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-20T04:41:33Z"
updated = "2026-10-20T04:41:33Z"
scope = ["crates/frob-obligations/src/tick_protect.rs"]
+++

found while working ~ZK2SR2P: classic protection 404 'Branch not protected' gives a false Error when a ruleset protects the branch; query /repos/o/r/rules/branches/{branch}
