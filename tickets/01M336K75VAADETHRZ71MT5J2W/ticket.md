+++
id = "01M336K75VAADETHRZ71MT5J2W"
title = "WEBSEC injection substrate: sink/source registry (extends SEC005 taint gate)"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0NVJMAC21FPVPYYSEE"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5307"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/gates/_taint_gate.py", "src/frob/webapp/_websec_sinks.py", "tests/fixtures/webapp/websec1xx/**", "docs/modules/webapp-websec-injection.md", "tests/unit/test_websec_sinks.py", "frob.toml"]

[[links]]
kind = "blocked-by"
target = "01M336K75PBAVJE0SEABECQYQV"
+++

Verified: SEC005's taint substrate exists (src/frob/gates/_taint_gate.py, docs/modules/gates.md#rule-catalog, T-0781) -- this leaf extends it, it does not invent a parallel engine. New src/frob/webapp/_websec_sinks.py registry keyed by framework: sources (request params/headers/body/URL/cookies/filenames across Flask/Django/Express/Rails/FastAPI), sinks (innerHTML/outerHTML/document.write/insertAdjacentHTML for JS/TS AST; dangerouslySetInnerHTML for JSX; v-html for Vue SFC template block; Jinja |safe/autoescape=False, Django mark_safe/autoescape-off, Rails .html_safe/raw() as TEXT-REGEX rules over template files, not tree-sitter). Fixture: tests/fixtures/webapp/websec1xx/ with one file per sink planting exactly the finding.
