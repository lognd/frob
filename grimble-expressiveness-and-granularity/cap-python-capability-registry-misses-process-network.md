+++
id = "01M6422ZVVSTEKVMY0PR269X33"
title = "CAP: Python capability registry misses process, network, environment, native-library and deserialization entry points"
type = "task"
category = "todo"
priority = "high"
points = 8
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:47:39Z"
updated = "2026-10-29T14:47:39Z"
idempotency_key = "vnvd3q1-py-api-gaps"
scope = ["crates/grimble-check/**,crates/gob-symbols/**,crates/gob-caps/**"]

[[acceptance]]
text = "each entry point of the os exec/spawn family, pty, asyncio subprocess, http.client, urllib3, httpx, smtplib, ftplib, asyncio streams, os.environ reads, ctypes loaders, pickle loads and archive extraction is registered and tested"
bound = false
+++

Cases p15 p16 p17 p18 p19 p25. symbol-resolved fix required (binding/import resolution, not text matching); pin case as regression test; unresolvable forms must report Unresolved, never pass silently
