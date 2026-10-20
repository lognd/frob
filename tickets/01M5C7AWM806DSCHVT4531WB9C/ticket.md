+++
id = "01M5C7AWM806DSCHVT4531WB9C"
title = "frob enumerates live repo packs (with tree digests) for check --trust-from"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-20T08:37:34Z"
updated = "2026-10-20T08:37:34Z"
scope = ["crates/frob-check/src/**"]
+++

found while working ~X625YAT: --trust-from currently passes an empty live-pack list, so no pack is ever flagged from frob; enumerate repo packs and their tree digests. Also consider a dedicated rule id instead of PACK001, and verify ci.yml has origin/experimental (fetch-depth 0).
