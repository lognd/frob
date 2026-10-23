+++
id = "01M5HGRWG7RDR3DTS7PT08HTWJ"
title = "Wire UNITY301 and UNITY302 into grimble-check"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T09:58:42Z"
updated = "2026-10-23T01:39:38Z"
scope = ["crates/grimble-check/**", "crates/grimble-lints/**", "docs/**"]

[[acceptance]]
text = "Given a Unity project whose input settings trip UNITY301, when grimble check runs, then UNITY301 is reported through a registered rule with a docs page"
bound = false

[[acceptance]]
text = "Given a Unity project whose physics settings trip UNITY302, when grimble check runs, then UNITY302 is reported through a registered rule with a docs page"
bound = false
+++

Found while working ~3XRQ6RM. grimble_lints::unity_input::scan and unity_physics::scan are detector libraries only. Declare UNITY301/UNITY302 as #[rule]s with mdtest pages, add a pass (read ProjectSettings/ProjectSettings.asset via unity_input::active_input_handler; not_applicable when absent), and wire into grimble-check product, host and report cache like PATH/TIME.
