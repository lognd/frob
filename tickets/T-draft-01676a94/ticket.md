---
id: T-draft-01676a94
title: 'WEBSEC injection and output encoding: XSS sinks, SSTI, eval/exec, unsafe deserialization,
  command/NoSQL/LDAP/log/header injection, input bounds (ASVS V1 V2 V5 V15)'
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
attachments:
- path: T-draft-01676a94/attachments/01-untitled.md
  caption: ''
  sha256: 36bf676a8ecff02829fe5d2bf2d8e50874036895a86966819d181bf329561761
threat: tampering
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
28 entries in the attached corpus, 25 static. Sinks by framework: innerHTML, dangerouslySetInnerHTML, v-html, Jinja |safe and autoescape=False, Django mark_safe, Rails raw/html_safe; yaml.load without SafeLoader, pickle.loads on untrusted, subprocess shell=True with non-literal argv, eval/exec/Function; CRLF in log calls, header values from input; XML parsers with external entities; JSON/XML depth and size limits. Each rule reason cites the ASVS 5.0 id and CWE from the corpus. Frob's existing SEC005 taint substrate is the engine: extend sources (request params, headers, body, URL, cookies, file names) and sinks per framework.