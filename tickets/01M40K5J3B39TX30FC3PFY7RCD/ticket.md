+++
id = "01M40K5J3B39TX30FC3PFY7RCD"
title = "ticket evidence add: a --ref value starting with a hyphen is parsed as a flag"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T09:57:47Z"
updated = "2026-10-03T10:09:42Z"
idempotency_key = "m2-evidence-ref-hyphen"
labels = ["milestone:2", "release:0.532.0"]
scope = ["crates/frob-evidence/**", "crates/frob/src/milestone_evidence_cmd.rs", "crates/frob/tests/**"]

[[acceptance]]
text = "Given --ref -p frob-cli -E 'test(x)', when ticket evidence add runs, then the filter is taken whole"
bound = false

[[acceptance]]
text = "Given a nextest filter matching zero tests, when evidence add runs, then nothing is recorded and the message says the filter matched nothing"
bound = false
+++

Every agent recording nextest evidence hit this: --ref -p frob-cli fails because clap reads -p as a flag, so they write --ref="-p ..." or record failed attempts with filters that match nothing. The --ref argument takes one opaque value (a filter, a command, a path): set allow_hyphen_values on it (and on milestone evidence add), and add a test with --ref -p crate -E 'test(x)'. Also: a nextest filter that matches zero tests must refuse to record (exit with a teaching message) instead of storing a failed measurement, since three agents left failed evidence records this way.
