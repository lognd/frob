+++
id = "01M336K75TSH3S8P5MHZCX4PG3"
title = "WEBSEC101-108: output-encoding and template sinks"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M2Y1SS0NVJMAC21FPVPYYSEE"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5306"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_websec_xss.py", "tests/fixtures/webapp/websec1xx/xss/**", "docs/modules/webapp-websec-xss.md", "tests/unit/test_websec_xss.py"]

[[links]]
kind = "blocked-by"
target = "01M336K75VAADETHRZ71MT5J2W"
+++

Rule ids WEBSEC101 (reflected/stored XSS encoding, ASVS V1.2.1), 102 (innerHTML/outerHTML/document.write/insertAdjacentHTML JS/TS AST), 103 (dangerouslySetInnerHTML JSX), 104 (v-html Vue SFC), 105 (Jinja |safe/autoescape=False regex), 106 (Django mark_safe/autoescape-off Python AST + template regex), 107 (Rails .html_safe/raw() regex), 108 (PHP echo of superglobals without htmlspecialchars, regex). Dispatched by framework detection (WEBSUB-2) so a Django-only repo never runs the Rails rule. Fixture: one planted finding per rule id.
