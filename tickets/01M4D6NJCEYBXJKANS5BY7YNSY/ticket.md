+++
id = "01M4D6NJCEYBXJKANS5BY7YNSY"
title = "gob-git/gob-walk: one repository, index and filter pipeline per process; hash each file once"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-10-08T07:29:28Z"
updated = "2026-10-10T00:12:15Z"
labels = ["creates:crates/gob-git/tests/shared_reader.rs"]
scope = ["changelog.d/**", "crates/gob-git/src/content.rs", "crates/gob-git/tests/shared_reader.rs"]

[[acceptance]]
text = "Given a warm grimble check, when traced, then the repository and index are opened once and each file hashed once"
bound = true
+++

notes/research/profile-2026-10-07.md section 5 item 9 (content.rs:144 WorktreeSource::with_reader per rayon chunk).
