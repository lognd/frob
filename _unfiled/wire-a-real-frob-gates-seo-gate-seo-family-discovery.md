+++
id = "01M38BCNC8TEY8XYHGVEE5FKM3"
title = "Wire a real frob.gates._seo_gate (SEO family discovery)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5512"]
scope = ["src/frob/gates/_taint_gate.py", "tests/unit/test_seo_crawl.py", "tests/unit/test_webapp_webperf_markup.py", "tests/fixtures/webapp/webperf1xx/markup/webperf101_positive/next.config.js"]
+++

found while working T-5374: docs/modules/webapp-seo.md defines no leaf-hook convention, so no live gate calls src/frob/webapp/_seo_tags.py's websec_findings hook (frob.gates._taint_gate only discovers frob.webapp._websec_* modules by name prefix, and _seo_tags does not match it). Mirror frob.gates._a11y_gate's pkgutil-discovery pattern (T-5323) for a new frob.gates._seo_gate over frob.webapp._seo_* modules, and register it in gates/__init__.py (_ALL_GATES, _CANONICAL_GATE_ORDER, _build_process_jobs, _KNOWN_GATE_RULES for SEO101-112). Coordinate with sibling SEO leaves (T-5365 spam, T-5362 crawl) since they hit the same gap.
