+++
id = "01M4NZCSJWT2XSEZQBVPNMA6HM"
title = "Evidence events store a test count and digest, not the full test-name list"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-11T17:15:30Z"
updated = "2026-10-11T17:55:13Z"
scope = ["crates/frob-evidence/**", "crates/frob-ledger/**", "changelog.d/**", "crates/frob-tests/tests/selection.rs", "crates/frob-tests/tests/typescript.rs", "docs/design/tickets.md", "crates/gob-dev/src/import_v1.rs"]

[[acceptance]]
text = "Given an evidence run that matches 500 tests, when the event is written, then the event file holds the count and digest but not the 500 names and its size is under 2 KB"
bound = true

[[acceptance]]
text = "Given the artifact for that run, when read by digest, then the full test-name list is still there"
bound = true

[[acceptance]]
text = "Given an evidence ref matching more than 50 tests, when evidence add runs, then a warning names the count and suggests exact-name refs"
bound = true
+++

Evidence events (kind=evidence) carry the full tests = [...] name list, up to 70 KB per event. In the last 24 h evidence events were 4.2 MB of the 4.4 MB of new ledger bytes (95%), about 20x the code added. They cost clone, checkout, fold and CI time and any agent that reads them. Keep a test count and the digest in the event; keep the full list only in the artifact file under .git/frob/artifacts/<digest>. Also warn (not refuse) from 'evidence add' when a ref matches more than 50 tests, pointing at exact-name refs.
