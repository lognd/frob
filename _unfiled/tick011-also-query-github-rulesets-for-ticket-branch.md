+++
id = "01M5BSTR1AMEEDFQMDRR4JF26Z"
title = "TICK011: also query GitHub rulesets for ticket branch protection"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T04:41:33Z"
updated = "2026-10-28T12:55:59Z"
labels = ["no-story"]
scope = ["crates/frob-obligations/src/tick_protect.rs"]
+++

found while working ~ZK2SR2P: classic protection 404 'Branch not protected' gives a false Error when a ruleset protects the branch; query /repos/o/r/rules/branches/{branch}

no-story: internal engineering task in frob-obligations; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
