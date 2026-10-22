+++
id = "01M5HQMX1NFZNV3R465V2DWJA2"
title = "Update grl-spec and grimble docs: needs is capabilities, reads is side relations"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-22T11:58:51Z"
updated = "2026-10-22T14:50:31Z"
scope = ["docs/design/grl-spec.md", "docs/grimble/**"]

[[acceptance]]
text = "Given grl-spec sections 4-6 and the grimble sysdesign pack page, when read, then needs names capabilities and diff, lease, config and model appear under reads"
bound = false
+++

found while working ~54ECDV7: needs now names language capabilities and side relations (diff, lease, config, model) moved to a reads header; grl-spec sections 4-6 and docs/grimble/packs/grimble-sysdesign.md still show needs diff/model.
