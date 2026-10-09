+++
id = "01M4FGYK3ZMG2PFK5FF7N3TMXS"
title = "grmb-spec: a claim form for threat and data assumptions without a flow proposition"
type = "docs"
category = "todo"
priority = "medium"
points = 3
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T05:07:38Z"
updated = "2026-10-09T05:07:38Z"
idempotency_key = "logand-gaps-D5"
labels = ["adoption:logand-app", "grimble"]
scope = ["docs/design/grmb-spec.md", "docs/design/grimble-model.md", "changelog.d/**"]

[[acceptance]]
text = "Given the decision, when grmb-spec section 4 is read, then it states the proposition kind, its fields, its verdict (Unresolved without evidence) and the MDL008 interaction"
bound = false

[[acceptance]]
text = "Given the 27 ported assumptions, when the doc is read, then it shows the target spelling of one CWE assumption and one PII assumption"
bound = false
+++

Repro 20-claim-needs-noflow-reach-bound (~/projects/frob-v2-repros/logand-grimble-20261009/20-claim-needs-noflow-reach-bound): 14.1 item 8 turns assume into claim but what is mandatory (MDL008) and only noflow/reach/bound exist, so 27 CWE and PII assumptions were ported as false noflow propositions that will read REFUTED once ~QNDWNDM and the kernel claim ticket land. Decide the form (for example an attests proposition with an owner and review date, resolved Unresolved until evidence) and write it in grmb-spec section 4 and grimble-model.md section 3.
