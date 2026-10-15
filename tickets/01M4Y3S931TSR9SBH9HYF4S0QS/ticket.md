+++
id = "01M4Y3S931TSR9SBH9HYF4S0QS"
title = "Replace placeholder packs/std/rules/TODO001.grl with real std sources"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-14T21:06:09Z"
updated = "2026-10-15T22:58:28Z"
scope = ["packs/std/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FYE5D1N2SY01VNVVACK"

[[acceptance]]
text = "Given the real std GRL sources, when cargo dev gen all --check runs, then it reports no GEN001 and no placeholder copy remains"
bound = true
+++

Follow-up of ~T5H07H5: packs/std/rules/TODO001.grl is a copy of the gob-plan corpus rule used to exercise std-rules codegen. Replace with the real std GRL sources once ~VNVVACK defines them and regenerate.
