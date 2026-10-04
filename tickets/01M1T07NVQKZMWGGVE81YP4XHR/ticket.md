+++
id = "01M1T07NVQKZMWGGVE81YP4XHR"
title = "waiver path for INV001/INV002"
type = "security"
category = "triage"
priority = "high"
parent = "01M1QDTYTRW714S858S0TP6YWM"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-09-06T00:00:00Z"
aliases = ["T-3959"]
labels = ["milestone:0.539.0", "v1-cluster:B4"]
scope = ["src/frob/gates/_inv.py", "src/frob/gates/_waive.py"]

[[acceptance]]
text = "given an invariant with no standing evidence and a reasoned frob:waive INV001 marker matching the INV003/INV004 mechanism, when frob check runs, then INV001 does not fire"
bound = false

[[acceptance]]
text = "given the same for INV002 with no code anchor, when frob check runs, then INV002 does not fire"
bound = false

[[acceptance]]
text = "given no waiver present, when frob check runs, then INV001/INV002 fire exactly as today"
bound = false
+++

Convergence 4 of T-3928 (threat-model item 8 + edge/ops item 6, arrived independently). VERIFIED via git grep of src/frob/gates/_inv.py: INV003 and INV004 each call _file_has_reasoned_doc_waiver(path, RULE) to honor a markdown-side <!-- frob:waive INV003/INV004 reason=... --> marker; INV001 and INV002 have no equivalent call anywhere in the file -- they are ERROR, ungated by binding, per the module's own docstring. FINDING THIS WOULD HAVE CAUGHT: an invariant describing a KNOWN, TICKETED-BUT-UNLANDED gap cannot be committed at all, because INV001 (no standing evidence) or INV002 (no code anchor) fires with no escape hatch -- the auditors' word for it is backwards: the system refuses to record a TRUE statement about the code because the thing it describes is not fixed yet. Edge/ops adds the cost: this is why invariants/ sits EMPTY in their repo and the invariant gate passes VACUOUSLY on every run -- a silent zero in frob's own invariant system, and it actively discourages writing invariants early when they are most valuable. Fix: give INV001/INV002 the same doc-waiver escape INV003/INV004 already have, so a WIP invariant can be committed honestly instead of omitted.
