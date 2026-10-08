+++
id = "01M4D91DTERJHX4TGJVV4KM7K8"
title = "Web profile: ESLint JSON parser; stages for eslint, typescript-eslint (type-aware, separate), jsx-a11y, react-hooks and eslint-plugin-react"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M4D8X558Q07HCMEBP224NQP4"
reporter = "lognd"
created = "2026-10-08T08:10:53Z"
updated = "2026-10-08T08:10:53Z"
scope = ["changelog.d/**", "crates/gob-check/**", "crates/frob/**"]

[[acceptance]]
text = "Given eslint -f json output, when parsed, then jsx-a11y ids map to A11Y, react-hooks to REACT, no-floating-promises to CONC and no-explicit-any to TYPING"
bound = false

[[acceptance]]
text = "Given the type-aware stage, when frob check runs, then its time is reported separately and outside the check budget"
bound = false
+++

notes/research/lint-catalogue-2026-10-08.md rows W01, W02, K17, K23 (4.2 N04); notes/research/creators-web-2026-10-08.md 4.1 (form-no-label 9 voices, effect-for-derived-state 8, alt-text 8) and 5.6 (type-aware rules cost a type check: separate stage outside the 2 s budget).
