+++
id = "01M5K3RAZWM6Z4GWWQ716JGSGC"
title = "Feed unity::scan and other language vocabularies into PAIR001"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-23T00:49:41Z"
updated = "2026-10-23T02:53:04Z"
scope = ["crates/grimble-lints/**"]

[[acceptance]]
text = "Given a Unity C# class that subscribes in OnEnable and never unsubscribes in OnDisable, when PAIR001 runs, then it is reported"
bound = false

[[acceptance]]
text = "Given a Unity class that pairs OnEnable and OnDisable correctly, when PAIR001 runs, then nothing is reported"
bound = false
+++

found while working G59GJ01: PAIR001 only runs effect::scan over TS/JS files; Unity OnEnable/OnDisable and other languages are not wired in.
