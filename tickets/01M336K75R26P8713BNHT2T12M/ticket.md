+++
id = "01M336K75R26P8713BNHT2T12M"
title = "New advisory Severity tier that never fails a gate (LAUNCH family)"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0MVHB8M891RN134SE7"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5304"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/gates/_models.py", "frob.toml", "docs/modules/gates.md", "src/frob/gates/_waive.py", "src/frob/check/_python.py", "src/frob/gates/_gates_schema.py", "src/frob/findings.py"]
+++

OWNER DIRECTIVE: LAUNCH gets a NEW `advisory` Severity tier, not a never-fail flag bolted onto `warn`. Locate the existing Severity enum (grep frob.gates for `class Severity` -- likely src/frob/gates/_models.py or frob/findings) and add ADVISORY as a real member; the finding-rendering path (`frob check` output, `--report` surfaces) must render advisory findings distinctly from warn (never counted toward a non-zero exit, never gate-blocking, still visible). [gates.severity] parsing must accept the string 'advisory' as a valid per-rule override value. T-5145-6 (LAUNCH checklist) blocks on this leaf. Doc: docs/modules/gates.md's severity-tier explanation.
