+++
id = "01M4M5CQ9529KH526299QXXFVF"
title = "grimble: GRL compile verb that checks rule files and prints compile_report"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-11T00:21:50Z"
updated = "2026-10-11T03:39:04Z"
scope = ["crates/grimble/**", "crates/gob-plan/**", "changelog.d/**", "docs/**", "crates/gob-dev/profile.toml"]

[[acceptance]]
text = "Given a .grl file with an unknown kind, when the grimble verb runs on it, then it exits non-zero and prints the GRL diagnostic from compile_report"
bound = true

[[acceptance]]
text = "Given a valid .grl file, when the verb runs, then it exits 0 with no diagnostics"
bound = true
+++

No shipped binary compiles GRL; check_file_with and compile_report have no caller. Add a grimble verb that reads .grl files and prints gob_plan::check::compile_report.
