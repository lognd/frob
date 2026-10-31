+++
id = "01M68WXFYP1C9HTSGY191SCYJP"
title = "HTTP layer: axios instances, baseURL and ky prefixUrl resolution"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-31T11:53:28Z"
updated = "2026-10-31T11:53:28Z"
scope = ["crates/gob-frameworks/**"]

[[acceptance]]
text = "axios.create({baseURL}) instances and their calls resolve the base so the edge is Must when the base is a known literal."
bound = false
+++

Found while working ~0ETTMMF. Currently any baseURL only marks the call open_prefix (May).
