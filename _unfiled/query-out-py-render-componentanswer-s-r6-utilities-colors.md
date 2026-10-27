+++
id = "01M1QDTV26DB9Z0N54XQ6MGVE2"
title = "query_out.py: render ComponentAnswer's r6 utilities/colors/spacings/layers fields"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:35Z"
aliases = ["crunk:T-0070"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/report/query_out.py", "tests/unit/test_report_query.py"]
+++

T-0064 extended ComponentAnswer (query/models.py) with utilities/colors/spacings/layers for jsx components (r6/CR-18), but report/query_out.py's render_query/render_query_json for kind=='component' only emit name/path/elements/modifiers/tokens -- found while working T-0064, out of its declared scope (report/terminal.py + report/json_out.py only). E2E-26/CT-26 wants 'query component <TsxName>' to list literal facts via the CLI; today that only works at the engine level (component_card's ComponentAnswer), not through the CLI's human/JSON renderers.
