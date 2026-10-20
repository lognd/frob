+++
id = "01M30M6G4N085W95VEQTJT2PGY"
title = "frob doctor: report lint-tool version lag against latest PyPI/npm/crates release"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-21T00:00:00Z"
updated = "2026-09-21T00:00:02Z"
aliases = ["T-5269"]
scope = ["src/frob/doctor.py"]
+++

T-5138 acceptance [5] (given ruff two minor versions behind PyPI, frob doctor reports the lag) is out of T-5138's declared scope (src/frob/vet/*.py, frob.toml, docs/modules/vet.md, src/frob/strata/_cve_fingerprint.py -- doctor.py is not in it). DESIGN item 7 from T-5138: frob doctor reports installed ruff/ty/mypy/eslint/clippy versions against the latest PyPI/npm/crates release, cached 24h, warns past a configurable lag.

## Drop reason
- 2026-09-22: duplicate of T-5204 -- identical title/body (frob doctor lint-tool version lag), both filed from the same T-5138 DESIGN item 7 follow-up (absorbed by T-5204)
