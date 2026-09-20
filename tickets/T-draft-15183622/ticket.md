---
id: T-draft-15183622
title: 'WEBSEC session, authentication and cryptography: CSRF, cookie flags, fixation
  and timeout, JWT and OAuth checks, NIST 800-63B passwords, hashing, IV/nonce, randomness,
  TLS verification (ASVS V6 V7 V9 V10 V11 V12)'
state: queued
kind: security
origin: human
created: '2026-09-20'
priority: critical
parent: T-draft-09897a86
tier: story
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: spoofing
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
34 entries, 25 static, 7 config, 4 dynamic-only -> test obligations. Static rules: state-changing route on GET; CSRF middleware absent in Django/Flask/Express/Rails config; cookie without Secure/HttpOnly/SameSite; session id not rotated on login; no server-side logout invalidation; jwt.decode without algorithms allowlist or verify_exp; refresh token without rotation; OAuth client without state/PKCE; redirect_uri wildcard; password hashing via md5/sha1/plain vs bcrypt/argon2/scrypt; composition rules or max length below 64 (NIST 800-63B 5.1.1.2); ECB mode; static IV; random.random/Math.random for tokens; verify=False, rejectUnauthorized:false, http:// API base URLs; HSTS absent. Cites in corpus.