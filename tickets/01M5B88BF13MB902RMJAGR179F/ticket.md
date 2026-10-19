+++
id = "01M5B88BF13MB902RMJAGR179F"
title = "Model: grant or excuse net.listen for loopback fake servers in frob-mirror tests (CAP001)"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-19T23:34:25Z"
updated = "2026-10-19T23:34:25Z"
scope = ["design/model.grmb"]
+++

found while working ~P4A6YB2: crates/frob-mirror/src/github/http.rs tests bind a loopback TcpListener; CAP001 reports node/frob net.listen with no grant. Add an excuses/grant in design/model.grmb.
