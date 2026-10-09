+++
id = "01M4DYPHVAG574Z9ZJZ41PCRHB"
title = "Wire check_file_with and compile_report to the config schema the binary ships"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-08T14:29:26Z"
updated = "2026-10-08T14:29:26Z"
scope = ["changelog.d/**", "crates/gob-plan/**", "crates/grimble/**"]

[[acceptance]]
text = "Given a GRL rule with a misspelt config column, when compiled by the shipped binary, then GRL001 names the column"
bound = false
+++

Follow-up from ~CDMAECH/~ZKM5W7Y; needs ~PHFBHDJ for row columns.
