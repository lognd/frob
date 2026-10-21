+++
id = "01M5F4J8QW4YYD20XP8KGTC9X2"
title = "Python adapter misses call nested in return inside def (r.keys)"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T11:46:53Z"
updated = "2026-10-21T11:46:53Z"
+++

Found by sysdesign STORE101: 'return r.keys("session:*")' inside a def did not match c.callee.name == "keys"; a bare statement call does. Investigate the python adapter call extraction.
