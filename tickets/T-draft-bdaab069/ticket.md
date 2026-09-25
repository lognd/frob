---
id: T-draft-bdaab069
title: close the marked authority gaps in sysdesign-research.md with primary sources
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-2532ae6a
tier: ticket
sprint: sysdesign
runs_last: false
milestone: 0.539.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- scratchpad/sysdesign-research.md
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator; research-corpus
  edit only
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: close the marked authority gaps in sysdesign-research.md with primary sources
kind: feature
tier: leaf
parent: T-SYS-SH
milestone: 0.539.0
sprint: sysdesign
points: 3
scope: scratchpad/sysdesign-research.md (only; a research-corpus edit, no source scope)
blocked_by: []

Body:

Per the research file's own "Fetches attempted and explicitly failed/blocked this pass" and
"Honest bottom line" sections, this pass left several requested authorities un-incorporated or
only title-cited:
- NIST SP 800-41 Rev. 1 ("Guidelines on Firewalls and Firewall Policy") -- csrc.nist.gov served
  a frame-buster/redirect page; the underlying PDF text was never fetched. Rows 4.1, 4.4, 4.6
  cite the document by title/number only.
- Netflix engineering material -- attempted (netflixtechblog.com, Medium-hosted) and blocked by
  Cloudflare bot protection.
- Shopify, Discord, Uber first-party engineering posts -- not attempted in the original pass,
  despite being explicitly named authorities.
- Kubernetes NetworkPolicy docs, Kubernetes Deployment rolling-update strategy
  (`maxUnavailable`/`maxSurge`) docs, 12-Factor "Logs" and "Dev/prod parity" factor pages --
  not fetched.
- DNS-specific and HTTP/2-3-specific rows (1.1, 1.3) and several load-balancing rows (2.6, 2.8,
  2.10) lack a directly quotable line even though the general area was fetched.

Acceptance criteria: re-attempt each fetch above (via a real browser-shaped fetch for the
Cloudflare-blocked Netflix post, and the NIST PDF specifically rather than the HTML frame-
buster URL); update the corresponding rows in sysdesign-research.md in place with a verbatim
quote and citation, or, where a fetch genuinely cannot be completed, leave the row's existing
gap note intact rather than inventing a quote. Update the "Coverage checklist" section's
per-item source status to reflect what changed. This ticket unblocks C1 (DNS), C6 (NIST-cited
firewall rows), C7 (mTLS), and G7 (multi-region RPO/RTO posture).
