+++
id = "01M35RZY79XWZ51X4BTB6S7CAA"
title = "WEBSEC218-225: password policy and storage"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0PCVWFZPFZT8VQ159Z"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5353"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_websec_password.py", "tests/fixtures/webapp/websec2xx/password/**", "tests/unit/test_websec_password.py", "docs/modules/webapp-websec-password.md"]

[[links]]
kind = "blocked-by"
target = "01M336K775CA7W9WDYAD339SEK"
+++

Email verification gating privileged actions, breach-password check (NIST 800-63B 5.1.1.2), password hashing algorithm (bcrypt/argon2/scrypt vs md5/sha1/plaintext), ECB mode, static IV/nonce reuse, default accounts in seed/migration data, password verified without silent truncation/case-folding. AST lint per sink. Fixture per rule id.
