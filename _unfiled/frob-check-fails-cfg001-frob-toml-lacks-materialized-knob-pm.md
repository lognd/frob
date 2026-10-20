+++
id = "01M42DGVJK4AGTMTXP30TPDGB3"
title = "frob check fails CFG001: frob.toml lacks materialized knob pm.strict"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "lognd"
created = "2026-10-04T02:57:35Z"
updated = "2026-10-04T03:00:08Z"
scope = ["frob.toml"]

[[acceptance]]
text = "Given this repository's frob.toml, when frob check runs, then no CFG001 finding is reported"
bound = true
+++

found while working ~3YYNHAC; cargo dev ci --step check fails only on CFG001 (run frob config sync)
