+++
id = "01M4D6NFCDSW5E4FD9X8J3BE8W"
title = "frob-land: one check pass, a stable shared target dir for land checkouts, background worktree removal"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-10-08T07:29:25Z"
updated = "2026-10-09T19:03:42Z"
scope = ["changelog.d/**", "crates/gob-fs/tests/inventory.rs", "crates/frob-land/src/land.rs", "crates/frob-land/src/ratchet.rs"]

[[acceptance]]
text = "Given a land whose merge is a no-op, when it runs, then the check runs once and the tool stages reuse a persistent target dir; measured land time is reported in the done-report"
bound = true
+++

notes/research/profile-2026-10-07.md section 5 item 4: land took 452 s and 643 s; it runs the pipeline three times and builds cargo from an empty target twice (clippy 45-100 s, gen check 69-209 s).
