+++
id = "01M68WXG18DSY9X054CAQ6N312"
title = "HTTP layer: cross-file router prefixes (include_router, register_blueprint, router.use, axum nest/merge)"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-31T11:53:28Z"
updated = "2026-10-31T11:53:28Z"
scope = ["crates/gob-frameworks/**"]

[[acceptance]]
text = "A FastAPI APIRouter included in another file, a Flask blueprint, an Express router.use and an axum router built in another function or merged get the full prefix."
bound = false
+++

Found while working ~0ETTMMF. Prefixes are only resolved within one file or one expression chain today.
