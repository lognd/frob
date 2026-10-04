+++
id = "01M3AXSD8QQWQHVBX0TT9PCATG"
title = "SYSDESIGN108: declared `may` egress capability with no matching firewall/NAT egress allow-rule"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD8RPMPFSYCWPM0XQY5G"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:24Z"
aliases = ["T-6423"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/sysdesign/_segmentation.py", "tests/fixtures/sysdesign/sysdesign108/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD8HXYDTWRT25J4YX5HQ"
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN108: declared may egress capability with no matching firewall/NAT egress
       allow-rule
kind: feature
tier: leaf
parent: T-SYS-SC
milestone: 0.539.0
sprint: sysdesign
points: 2
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_segmentation.py, docs/modules/gates.md (SYSDESIGN108 row),
       tests/fixtures/sysdesign/sysdesign108/**
blocked_by: [T-SYS-B-TERRAFORM]
tag: Static: design + Static: config (declared-vs-observed)

Research row 4.4 (egress control) combined with the expressiveness correction
(STRATA-EXPRESSIVENESS.md section D "egress control"): "`may 'net.out:stripe.com'` (MayGrant
capability atoms, _models.py:386 comment, node_prop `may` clause) already models exactly this
-- a node's declared outbound network capability -- so this is actually EXPRESSIBLE, not a
gap." This rule is the declared-vs-observed pairing SYSDESIGN needs on top of that existing
grammar: a design-model `may` grant with no corresponding egress allow-rule in the deployed
firewall config is either an unenforced capability declaration or a missing config entry, and
either way is worth flagging (same two-step declared/proven discipline as REL220/221).

Acceptance criteria: cross-references strata `may` capability atoms against T-SYS-B-TERRAFORM's
security-group/NACL egress rules for the same node's deployment target; flags a `may` grant
with no matching egress allow. Positive-control fixture: tests/fixtures/sysdesign/
sysdesign108/may-grant-no-egress-rule/**.
