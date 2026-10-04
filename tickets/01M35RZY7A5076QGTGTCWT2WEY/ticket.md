+++
id = "01M35RZY7A5076QGTGTCWT2WEY"
title = "WEBSEC226-230: randomness and TLS verification"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0PCVWFZPFZT8VQ159Z"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5354"]
labels = ["milestone:0.534.0"]
scope = ["tests/fixtures/webapp/websec2xx/random_tls/**", "src/frob/webapp/_websec_random_tls.py", "tests/unit/test_websec_random_tls.py", "docs/modules/webapp-websec-random-tls.md"]

[[links]]
kind = "blocked-by"
target = "01M336K775CA7W9WDYAD339SEK"
+++

Math.random()/random.random() used for a token/session-id/API-key/CSRF-token (name-based heuristic on the assignment target, PERF-family lexical-smell precedent), TLS verification disabled (requests verify=False/rejectUnauthorized:false/literal http:// to an API), TLS minimum version config, certificate pinning (mobile-only, config advisory), credential-stuffing rate-limit cross-refs 5144-2's rate-limit rule. HSTS is owned by T-5143-2's header-lint substrate, NOT this leaf -- this leaf blocks on it rather than reimplementing header parsing. Fixture per rule id.
