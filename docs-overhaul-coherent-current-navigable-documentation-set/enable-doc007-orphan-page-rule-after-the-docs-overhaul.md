+++
id = "01M67YBBB77TG1WNZ1VDEPQFYE"
title = "Enable DOC007 orphan-page rule after the docs overhaul"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M67VDQ8WGS0SYG4J4NFXNQJE"
reporter = "lognd"
created = "2026-10-31T02:59:16Z"
updated = "2026-10-31T02:59:16Z"
scope = ["frob.toml", "docs/**"]

[[acceptance]]
text = "DOC007 is on (its [rules.DOC007] off entry is removed from frob.toml) and frob check reports no orphan page under docs/"
bound = false
+++

Follow-up of ~XV82RW9: DOC007 ships severity off until the docs overhaul links or retires every orphan page. Remove the off entry, link or mark historical each reported page.
