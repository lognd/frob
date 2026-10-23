+++
id = "01M1QDTV1YJ6HC5CW905KQDHBH"
title = "R6-C: TW rule family, jsx never-fixable guard, utility-first org behavior (CR-17 rules, CR-21)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:02Z"
aliases = ["crunk:T-0062"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/rules/**", "src/crunk/spec/models.py", "tests/unit/test_rules_tailwind.py", "tests/unit/test_rules_org.py", "tests/unit/test_rules_color.py", "tests/system/test_e2e_24_25_jsx.py", "tests/system/test_e2e_29_utility_first.py"]

[[links]]
kind = "blocked-by"
target = "01M1QDTV1WHKSQHWQY5KASC9GH"

[[acceptance]]
text = "given the jsx/tailwind fixture, when check runs, then style-prop drift yields COLOR001/SPACE001 (never fixable), arbitrary values yield TW001 with nearest-token naming, an undefined theme mapping yields TW002, and utility-first mode silences ORG001/ORG003 while keeping the value rules (E2E-24/25/29)"
bound = false
+++

Per r6 rules.md (_tailwind.py TW001/TW002 semantics, JSX fixability paragraph, Org model paragraph; UT-RUL-TW/JSXFIX/ORGMODEL): TW catalog rows land in spec/models (('TW',1,error),('TW',2,error)); _fixable_sheet guard in _waive.py consulted by _color/_scales fix emission; org rules honor spec.org.model; engine registers tw rules. E2E fixtures mirror the field cases (style background '#000' + width 44; bg-[#282828] p-[13px]; theme entry to an undefined var).
