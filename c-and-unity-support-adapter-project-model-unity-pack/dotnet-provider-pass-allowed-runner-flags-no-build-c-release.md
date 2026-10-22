+++
id = "01M4DYPG8A4CEY04ARSW3H4AJR"
title = "dotnet provider: pass allowed runner flags (--no-build, -c Release) and register [evidence.dotnet] in FrobConfig::load"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-08T14:29:24Z"
updated = "2026-10-22T09:09:02Z"
scope = ["changelog.d/**", "crates/frob-evidence/**", "crates/frob/**", "docs/design/build-test-ci.md"]

[[acceptance]]
text = "Given --no-build in the evidence ref, when recorded, then it is accepted; given [evidence.dotnet] in frob.toml, when doctor runs, then it validates"
bound = true
+++

Follow-ups from ~9W0WEA9.
