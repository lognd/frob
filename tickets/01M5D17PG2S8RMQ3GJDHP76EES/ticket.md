+++
id = "01M5D17PG2S8RMQ3GJDHP76EES"
title = "DT04 flip step: goway with_refs, frob.toml orphan mode and ticket migrate"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T16:10:12Z"
updated = "2026-10-20T16:54:21Z"
scope = ["goway.toml", "frob.toml", ".gitattributes"]

[[links]]
kind = "blocked-by"
target = "01M5D1GP019PAH0KZPFNH0VAHZ"
+++

Found while working ~X2S3S24. At flip time: add refs/heads/frob-tickets and refs/remotes/origin/frob-tickets to goway.toml with_refs (goway refuses missing refs, so only after the branch exists locally), set ref_mode = orphan and ref in frob.toml, update .gitattributes, run frob ticket migrate --to-branch once. The guard test goway_syncs_the_ticket_branch_in_orphan_mode fails if with_refs is forgotten.
