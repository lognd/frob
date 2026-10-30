+++
id = "01M65MN85Z2KADZG0PN5R6GZCG"
title = "CAP: Python connection-object and asyncio loop methods are not registered"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-30T05:31:26Z"
updated = "2026-10-30T05:31:26Z"
scope = ["crates/gob-symbols/**", "crates/grimble-bind/**"]
+++

found while working ~R269X33: http.client/smtplib/ftplib connection methods, asyncio loop.subprocess_exec/create_connection, requests.Session/head/patch, yaml/pandas/numpy pickle loaders are not typed or registered.
