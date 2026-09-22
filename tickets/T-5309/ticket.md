---
id: T-5309
title: 'WEBSEC109-116: code-injection and deserialization sinks'
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: T-5141
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_websec_deser.py
- tests/fixtures/webapp/websec1xx/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
SSTI (render_template_string/Template(userInput)), eval/exec/new Function, yaml.load without SafeLoader, pickle.load(s) on untrusted data, subprocess shell=True/os.system with interpolated input, LDAP filter string concatenation, NoSQL/Mongo operator-key injection (unsanitized $where/$gt/$ne from request JSON), LaTeX --shell-escape. Python AST (SEC005 substrate reuse) for most; LaTeX is a build-step regex scan of the compile invocation. Fixture per rule id.