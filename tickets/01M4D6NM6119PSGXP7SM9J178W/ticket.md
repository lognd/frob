+++
id = "01M4D6NM6119PSGXP7SM9J178W"
title = "frob doctor: cheap gc oracle (batched events) and no full dry-run gc pass unless asked"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-10-08T07:29:30Z"
updated = "2026-10-08T07:29:30Z"
scope = ["changelog.d/**", "crates/frob-worktree/**", "crates/frob/**"]

[[acceptance]]
text = "Given frob doctor, when timed on this repository, then it stays under 0.2 s warm"
bound = false
+++

notes/research/profile-2026-10-07.md section 5 item 12 (gc/glue.rs:39, doctor.rs:760).
