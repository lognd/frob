+++
id = "01M4DPJMH0KAMV38DMWTXC59AG"
title = "gob-git ledger: a CAS loser re-runs the local-edit check on retry; skipped sync paths are reported, not only logged"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T12:07:29Z"
updated = "2026-10-08T12:07:29Z"
scope = ["changelog.d/**", "crates/gob-git/**"]

[[acceptance]]
text = "Given a CAS retry, when it runs, then the local-edit check runs again; given a skipped sync path whose winner later fails to sync, then the checkout is reported stale"
bound = false
+++

Follow-ups from ~84HHHVK.
