+++
id = "01M30M6G4M2JRRZTAHMPS9NB0Z"
title = "register VET012 in _KNOWN_GATE_RULES and _osv.py's fetch_url edge in design/frob.strata"
type = "story"
flavour = "quality_objective"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-21T00:00:00Z"
updated = "2026-09-21T00:00:02Z"
aliases = ["T-5268"]
scope = ["src/frob/gates/_waive.py", "design/frob.strata"]
+++

T-5138 added VET012 (advisory data unavailable) as a real fired rule id in src/frob/vet/_scan.py, and rewired _osv.py from an osv-scanner subprocess to a direct urllib fetch_url call. Both src/frob/gates/_waive.py (_KNOWN_GATE_RULES, VET001-011 block) and design/frob.strata (the src/frob/vet/** node's 'may fetch_url via' edge, currently only _nvd.py/_registry.py) need updating, but both files were held by T-5121's in-progress lease at T-5138's close-out time so this ticket could not touch them -- see T-5138's Done report.

## Drop reason
- 2026-09-22: VET012 registration and fetch_url edge landed inside T-5138 (absorbed by T-5138)
