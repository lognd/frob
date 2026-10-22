+++
id = "01M4FD43P9VMJC9BE0KGEKVBBH"
title = "frob init: write tickets/** text eol=lf to .gitattributes when core.autocrlf is set; note [evidence] attesters origin in the upgrade guide"
type = "story"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T04:00:45Z"
updated = "2026-10-22T14:03:50Z"
labels = ["adoption:hullbreach"]
scope = ["crates/frob/**", "docs/guides/upgrade-from-v1.md", "changelog.d/**", "docs/reference/**"]

[[acceptance]]
text = "Given a repository with core.autocrlf=true, when frob init runs, then .gitattributes contains tickets/** text eol=lf and the init report says so; the upgrade guide explains that attesters defaults to the runner's git user.email"
bound = true
+++

Hullbreach game (E, F).
