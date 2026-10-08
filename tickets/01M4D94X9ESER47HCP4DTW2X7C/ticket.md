+++
id = "01M4D94X9ESER47HCP4DTW2X7C"
title = ".NET and Unity profile: dotnet build SARIF with Roslyn CA/IDE, VSTHRD and Microsoft.Unity.Analyzers, USP suppressors on"
type = "story"
category = "todo"
priority = "high"
points = 5
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-08T08:12:48Z"
updated = "2026-10-08T08:12:48Z"
scope = ["changelog.d/**", "crates/gob-check/**", "crates/frob/**"]

[[acceptance]]
text = "Given a Unity fixture with ?. on a MonoBehaviour field and an empty Update, when frob check runs the dotnet stage, then UNITY findings appear with source_rule UNT0008 and UNT0001"
bound = false

[[acceptance]]
text = "Given an engine-called private message method, when checked, then no IDE0051 dead-code finding is reported"
bound = false
+++

notes/research/lint-catalogue-2026-10-08.md rows U01, U04, K02, K14, K23 (4.2 N05); notes/research/creators-games-2026-10-08.md 5.1 ranks 1, 4-10 are Microsoft.Unity.Analyzers rules and 5.6 (ship the rules and the suppressors together). Depends on the SARIF parser in the bind-before-own epic.
