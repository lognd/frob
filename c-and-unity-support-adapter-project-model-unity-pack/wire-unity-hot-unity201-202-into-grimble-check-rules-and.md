+++
id = "01M5HPSP14N3NCX5TNA9XDR1GY"
title = "Wire unity_hot (UNITY201/202) into grimble-check rules and docs"
type = "task"
category = "in-progress"
priority = "low"
points = 3
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-22T11:44:00Z"
updated = "2026-10-23T01:20:56Z"
scope = ["crates/grimble-check/**", "crates/grimble-lints/**", "docs/**", "crates/grimble/src/explain_cmd.rs"]

[[acceptance]]
text = "Given GetComponent in Update, when grimble check runs, then UNITY201 is reported through a registered rule with a docs page"
bound = true

[[acceptance]]
text = "Given an allocation in Update, when grimble check runs, then UNITY202 is reported through a registered rule with a docs page"
bound = false
+++
