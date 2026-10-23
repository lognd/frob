+++
id = "01M1QDTV2T0YXCAQ2XPPR7NXPG"
title = "r9: frontend-shell audit findings A-034..A-039"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:03Z"
aliases = ["crunk:T-0090"]
labels = ["component:crunk", "source:crunk"]
scope = ["docs/design/*.md", "docs/design/subsystems/*.md"]

[[acceptance]]
text = "given A-034..A-039, when the design tree is read, then each maps to a contract change or a recorded roadmap entry"
bound = true
+++

Six findings copied from the adopting project's real audit. Build-now: A-034 Tailwind default-theme key collisions (H: bare-number spacing keys silently redefine Tailwind defaults; static default-key table + collision warning + namespace_keys mode), A-035 alpha-capable color emission + silent-alpha-modifier detection (TW003), A-036 .ts class-string scanning, A-037 unused tokens in report v2, A-038 investigate missed custom-prop/rgba-triple findings in the entry stylesheet. Roadmap: A-039 observed fg/bg pair contrast closure (needs ancestor-analysis design).
