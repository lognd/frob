+++
id = "01M41JTGCWXZWWSPXYM9QNMT4D"
title = "ticket fragment: a bug ticket's title is not a usable default sentence; require --sentence for bugs"
type = "task"
category = "in-progress"
priority = "low"
points = 1
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T19:10:59Z"
updated = "2026-10-03T19:12:16Z"
scope = ["crates/frob/src/ticket/**", "crates/frob-release/src/fragment.rs"]

[[acceptance]]
text = "Given a bug ticket, when ticket fragment runs without --sentence, then it exits 2 asking for a sentence that describes the fix"
bound = false
+++

Two 0.532.0 fragments (~G31XEZ3, ~992AN0Q) shipped the bug's title as the changelog line ('Evidence capture writes non-ASCII tool output into ledger event files'), which reads as a new defect. Bug titles describe the problem, so for type bug (and security, incident) ticket fragment should refuse to default the sentence from the title and ask for --sentence describing the change; other types keep the title default.
