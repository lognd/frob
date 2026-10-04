+++
id = "01M35RZYA3EDEVTN8C8KTAJGNY"
title = "Widen _a11y_gate file walk to include CSS/SCSS"
type = "bug"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:00Z"
aliases = ["T-5443"]
labels = ["v1-cluster:B2", "area:crunk"]
scope = ["src/frob/gates/_a11y_gate.py"]
+++

found while working T-5321: frob.gates._a11y_gate._A11Y_EXTENSIONS only covers html/vue/jsx/tsx, so frob.webapp._a11y_interaction's four CSS-declaration rules (A11Y117/120/121/122) are fully implemented and unit-tested but never actually invoked through the real gate (CSS files are never parsed/handed to any hook). Widen _A11Y_EXTENSIONS to include .css/.scss (frob.lang already parses both via T-5303) so these rules fire in frob check.
