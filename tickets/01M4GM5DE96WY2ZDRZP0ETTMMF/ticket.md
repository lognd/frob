+++
id = "01M4GM5DE96WY2ZDRZP0ETTMMF"
title = "Server route and client call-site extraction (FastAPI, Flask, axum, Express; fetch/axios/ky) so cross-language impl hops match by method and path"
type = "story"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-09T15:23:02Z"
updated = "2026-10-09T15:23:03Z"
labels = ["grimble"]
scope = ["crates/gob-frameworks/**", "changelog.d/**"]

[[links]]
kind = "relates"
target = "01M4FDAD29CBF7S4EM2FKR5TXQ"

[[acceptance]]
text = "Given a TSX component calling fetch('/api/orders', {method: 'POST'}) and a FastAPI route @router.post('/api/orders'), when the framework layer runs, then both are extracted with method and path template and matched as one cross-language edge (May when the path is built dynamically, Unknown when opaque)"
bound = false
+++

Needed by grmb planning impl chains (owner 2026-10-09: ui button -> API -> ... traceable). gob-frameworks today extracts Next.js and React Router routes only.
