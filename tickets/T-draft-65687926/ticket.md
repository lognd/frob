---
id: T-draft-65687926
title: 'COMPLY: required pages, disclosures and config for CCPA/CPRA, CalOPPA, GDPR
  and ePrivacy, UK, Canada, Brazil, Australia, Japan, India, US state laws, HIPAA/GLBA/COPPA/FERPA,
  AI transparency laws, CASL/CAN-SPAM/TCPA, DSA, breach notification -- each rule
  cites the section'
state: queued
kind: feature
origin: human
created: '2026-09-20'
priority: high
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
- path: T-draft-65687926/attachments/01-untitled.md
  caption: ''
  sha256: 222540cfb6cba4460c966de63fcc149803e7e5c4523692a30220745d8f98865e
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
36 entries here plus 22 in lint-authorities.md section A and 14 in section G (litigation and enforcement patterns: ADA/Unruh accessibility suits, CIPA session-replay and pixel wiretap suits, VPPA, BIPA, FTC click-to-cancel and dark patterns, TCPA SMS, COPPA 2025 rule, state privacy laws with GPC, health data laws, cookie consent fines, EU AI Act Art. 50, California AI laws, NYC LL144, breach rules, age verification). 26 entries are BLOCKED on statute text fetch and carry the official-domain citation only; the implementer re-fetches and quotes before shipping the rule text. Rule shape: (a) required-page checks keyed on what the repo does: collects email -> privacy policy page with the CalOPPA 22575(b) contents and CCPA 1798.130 sections; uses AI on user data -> terms of service with AI disclosure and EU AI Act Art. 50 chatbot notice; has subscriptions -> cancel path of equal prominence (16 CFR 425, Cal. B&P 17600); sells/shares -> Do Not Sell link and GPC signal handling in consent code; sends SMS -> TCPA consent capture; embeds session replay, chat widget or Meta pixel -> disclosure and consent gate before load (CIPA 631/638.51, VPPA); processes health data outside HIPAA -> MHMDA consent; (b) config checks: analytics/pixel scripts loaded before consent in EU-targeted builds; data retention config absent for PII stores (ties to PII003); delete-my-data path: a request route or documented mailbox plus a 45-day (CCPA) / one-month (GDPR Art. 12(3)) SLA recorded; breach notification runbook present. Owner directive: delete-my-data reaches a human-read mailbox, clock starts at receipt, data-handling policy required.