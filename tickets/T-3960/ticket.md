---
id: T-3960
title: known-dangerous-comparison-idiom rule (substring vs prefix)
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: high
parent: T-3928
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_cve_fingerprint_scan.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a substring-containment check applied to a request-path, route, or identity-like
    variable, when frob check runs, then the new rule fires with a suggestion to use
    a prefix/exact/segment match
  evidence: []
- text: given a genuine substring search over free text (not a path/identity value),
    when frob check runs, then the rule stays quiet
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Convergence 5 of T-3928 (backend audit item 10 + threat-model item 5, arrived independently -- both call it cheap). Also T-3919 item 10 and T-3920 item 5 in those epics' own numbering; do NOT file separately there, cite this one. FINDING THIS WOULD HAVE CAUGHT: semantic authorization bugs from a substring test used where a prefix/exact check was needed -- e.g. a route-path or identity check using containment or startswith with the wrong operand order instead of a real path-segment or exact match, which is out of [[policy.pattern]] reach today (policy.pattern is a syntactic pattern surface, not a semantic-comparison-shape one). Proposed rule kind: a known-dangerous-comparison-idiom lint, structurally similar to the existing CVE-fingerprint scan (frob.strata._cve_fingerprint.CVE_FINGERPRINTS plus this gate's file) but for comparison-idiom needles rather than CVE needles -- e.g. flag substring containment used against a request path, route, or identity value where a prefix/exact/segment match is the security-relevant semantics. A small, cheap lexical/AST pattern lint per both auditors.
