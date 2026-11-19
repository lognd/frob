+++
id = "01M6PWX1T8YBXB9PE5H21YT2RK"
title = "grmb planning: derived V-model levels into kernel closure rules (orphan requirement, unjustified design)"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-05T22:22:35Z"
updated = "2026-11-19T03:58:07Z"
idempotency_key = "p4-vmodel-closure-followup"

[[acceptance]]
text = "Given a model with a requirement no design satisfies or a design that satisfies nothing, when the kernel closure rules run, then VMOD001 (orphan requirement) and VMOD002 (unjustified design) each fire once, and a satisfying design closes both"
bound = true
+++

Split from ~D4J3YZ2: the PLAN006 arm coverage and single-root-cause fix landed there, but the derived V-model levels feeding new kernel closure rules (orphan requirement, unjustified design and so on) were not built. Acceptance: Given a model with a requirement no design satisfies, When the closure runs, Then one finding names the orphan.
