+++
id = "01M4D90ZDHTSR1JX06Z17FNR3C"
title = "Python profile: ruff JSON parser, id map and frob init stage template"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M4D8X558Q07HCMEBP224NQP4"
reporter = "lognd"
created = "2026-10-08T08:10:39Z"
updated = "2026-10-08T08:10:39Z"
scope = ["changelog.d/**", "crates/gob-check/**", "crates/frob/**"]

[[acceptance]]
text = "Given ruff check --output-format=json output, when parsed, then F401 maps to DEAD, BLE001, E722 and S110 to ERR, ASYNC to CONC, PT to TESTQ and PLR2004 is off"
bound = false

[[acceptance]]
text = "Given frob init in a pyproject repository, when it writes frob.toml, then the ruff stage has a pinned version range"
bound = false
+++

notes/research/lint-catalogue-2026-10-08.md rows K02, K05, K14, K17, K20, K23, K34, K39 (4.2 N03); notes/research/mining-report-2026-10-08.md 3.4 Python stratum. PLR2004 (magic numbers) stays off: notes/research/lint-catalogue-2026-10-08.md 3.3.
