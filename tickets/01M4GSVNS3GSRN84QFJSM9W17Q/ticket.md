+++
id = "01M4GSVNS3GSRN84QFJSM9W17Q"
title = "Concurrent ledger writes (ticket new, update, evidence) race on .git/index.lock; retry with backoff instead of failing"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T17:02:34Z"
updated = "2026-10-10T02:21:09Z"
labels = ["adoption:hullbreach"]
scope = ["changelog.d/**", "crates/gob-git/src/ledger.rs", "crates/gob-git/tests/ledger.rs"]

[[acceptance]]
text = "Given several processes writing ledger events concurrently in one repository, when one finds .git/index.lock held, then it retries with bounded backoff (configurable via [git] cas_retries) and succeeds without the caller retrying"
bound = true
+++

hullbreach repro: agents writing tickets concurrently hit index.lock races; also seen here with ~15 agents. Related: ~W7NXA6R (land advance on index.lock), ~V58QYKH (coalesce writes).
