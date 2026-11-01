+++
id = "01M6B0TEBV67D42BHPEH4KGX4V"
title = "LOG001/LOG002: Python scripts and Node render helper (phase 4)"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T07:40:11Z"
updated = "2026-11-01T07:56:33Z"
scope = ["packaging/pypi/render.py,.github/scripts/**,scripts/claude-hooks/frob-suggest.py,crates/crunk-gallery/node/**", "packaging/pypi/render.py", ".github/scripts/**", "scripts/claude-hooks/frob-suggest.py"]

[[acceptance]]
text = "LOG001/LOG002 errors in the listed Python scripts are cleared (logging routed or justified frob:accept per site) and the .github/scripts unit tests still pass; repo-wide remainder is tracked by the sibling tickets"
bound = true
+++

Covers packaging/pypi/render.py, cone-compare.py, plan-jobs.py, frob-suggest.py and the gallery render.mjs.
