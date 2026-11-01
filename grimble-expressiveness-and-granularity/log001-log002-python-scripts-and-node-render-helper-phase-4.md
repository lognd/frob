+++
id = "01M6B0TEBV67D42BHPEH4KGX4V"
title = "LOG001/LOG002: Python scripts and Node render helper (phase 4)"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T07:40:11Z"
updated = "2026-11-01T07:48:05Z"
scope = ["packaging/pypi/render.py,.github/scripts/**,scripts/claude-hooks/frob-suggest.py,crates/crunk-gallery/node/**", "packaging/pypi/render.py", ".github/scripts/**"]

[[acceptance]]
text = "Python and Node LOG001/LOG002 sites are routed through logging or carry a justified frob:accept/exempt; grimble check --only LOG001,LOG002 reports zero errors repo-wide"
bound = false
+++

Covers packaging/pypi/render.py, cone-compare.py, plan-jobs.py, frob-suggest.py and the gallery render.mjs.
