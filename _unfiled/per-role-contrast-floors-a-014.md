+++
id = "01M1QDTV1K47NCWQG23QET33X2"
title = "per-role contrast floors (A-014)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:33Z"
aliases = ["crunk:T-0051"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/spec/models.py", "src/crunk/spec/load.py", "src/crunk/rules/_contrast.py", "src/crunk/report/terminal.py", "src/crunk/report/json_out.py", "src/crunk/app/app.py", "tests/unit/test_spec.py", "tests/unit/test_rules_contrast.py", "tests/unit/test_report.py", "tests/unit/test_app.py", "tests/system/test_e2e_22_floors.py", "tests/system/test_e2e_15_output.py"]

[[links]]
kind = "blocked-by"
target = "01M1QDTV1HBQD1X3VBA9MJ1ARV"

[[acceptance]]
text = "given a role declared { pair = [...], floor = 3.0 } whose ratio is 4.29, when check and check --contrast run, then that role passes with its own floor shown while an identical plain-pair role fails (E2E-22)"
bound = false
+++

Per r5 spec.md/rules.md/report.md: RolePair gains floor: float (gt 0) resolved at load -- plain [fg,bg] pairs get spec.models.CONTRAST_AA_FLOOR, the extended { pair, floor } table form overrides. contrast001 judges each pair against role.floor and names it in the message; render_contrast shows the per-role floor; render_contrast_json adds the floor field; App's --contrast exit derives from the per-role judgments (stop importing the global constant there). Field origin: a real 4.29 danger role needing the WCAG large-text exception.
