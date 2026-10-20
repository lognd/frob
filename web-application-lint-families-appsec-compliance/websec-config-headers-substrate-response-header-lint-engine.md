+++
id = "01M336K76D807X6VTTB7V8QPT1"
title = "WEBSEC config/headers substrate: response-header lint engine"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0Q1MXMXDHZ5ZJAD3XB"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5325"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_websec_headers.py", "tests/fixtures/webapp/websec3xx/**", "docs/modules/webapp-websec-headers.md", "tests/unit/test_webapp_websec_headers.py"]

[[links]]
kind = "blocked-by"
target = "01M336K75PBAVJE0SEABECQYQV"
+++

HeaderSourceKind union parser: (a) app-code AST lint for helmet(...)/django-secure/SECURE_* settings/manual response.headers[...]= calls, (b) nginx/Caddy config-file line parser for add_header/directive blocks, (c) documented gap for CDN-layer-only header injection (Cloudflare/Fastly dashboards) as a WARN advisory ('no in-repo evidence; confirm at your edge') rather than a false ERROR. Fixture: nginx conf, Django settings, Express+helmet fixture, one with and one without each header.
