+++
id = "01M68ZBTCYKQKKRXB8W75NWG1E"
title = "P1 grmb planning: U encoding (8.2) and fmt rules (8.3) with fixed-point worked examples"
type = "task"
category = "done"
outcome = "duplicate"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-31T12:36:14Z"
updated = "2026-10-31T13:14:40Z"
scope = ["crates/grimble-model/src/{adapter,fmt}.rs", "crates/grimble-model/tests/**"]

[[acceptance]]
text = "U term of every 8.2 construct matches its expect file"
bound = false

[[acceptance]]
text = "grimble fmt is a digest-preserving fixed point on sections 12 and 13"
bound = false
+++

Split from ~VKN98M6. U term of every planning construct per grmb-planning 8.2 with expect files; fmt per 8.3; web_app and thermostat examples are digest-preserving fmt fixed points. Also note spec drift: the original ticket text said -| and -? tokens, spec (D125/D129) says => and -!> only.
