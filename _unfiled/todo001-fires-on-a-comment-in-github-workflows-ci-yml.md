+++
id = "01M4FD3KT1XFB1N1GZYXFRMPT7"
title = "TODO001 fires on a comment in .github/workflows/ci.yml although YAML is not a scanned language for directives"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T04:00:28Z"
updated = "2026-10-10T20:19:26Z"
labels = ["adoption:hullbreach"]
scope = ["crates/frob-obligations/**", "crates/gob-directives/**", "changelog.d/**", "docs/reference/rules/TODO001.md"]

[[acceptance]]
text = "Given a TODO comment in a workflow YAML file, when frob check runs, then TODO001 follows the documented language set (no finding if YAML is unscanned, or docs updated if the decision is to scan YAML)"
bound = true
+++

Hullbreach game repro (D).
