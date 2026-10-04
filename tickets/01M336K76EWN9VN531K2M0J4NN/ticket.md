+++
id = "01M336K76EWN9VN531K2M0J4NN"
title = "WEBSEC301-309: security headers (CSP/HSTS/COOP/CORP/CORS/Cache-Control)"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0Q1MXMXDHZ5ZJAD3XB"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5326"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_websec_headers_rules.py", "tests/fixtures/webapp/websec3xx/headers/**", "tests/unit/test_websec_headers_rules.py", "docs/modules/webapp-websec-headers-rules.md"]

[[links]]
kind = "blocked-by"
target = "01M336K76D807X6VTTB7V8QPT1"
+++

CSP w/ nonce (ASVS V3.4.3), HSTS max-age>=31536000 (V3.4.1/V3.7.4), X-Content-Type-Options nosniff (V3.4.4), Referrer-Policy (V3.4.5), Permissions-Policy, COOP/COEP/CORP, CORS fixed/allowlisted origin (V3.4.2), CORS-preflight-reliance for sensitive functionality (V3.5.1/V3.5.2), Cache-Control no-store on authenticated responses (V14.3.2) -- this rule is the canonical owner of Cache-Control-on-authenticated-responses; T-5147-6 (WEBPERF server/network) blocks on this leaf rather than reimplementing the authenticated-route detection. Cache-key poisoning ships as a WARN advisory only (no ASVS id found in the corpus). Fixture per rule id via 5143-1.
