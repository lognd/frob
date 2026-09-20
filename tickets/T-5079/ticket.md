---
id: T-5079
title: 'DECISION: kernel extension domain 7/8 -- host/ACL (runs_as/unit/owns/listens/acl/sudoers/service_account),
  OS principals: desugar to the six primitives, or record as an extension?'
state: queued
kind: docs
origin: agent
created: '2026-09-19'
priority: medium
parent: T-4681
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: 'Owner records a decision in the body for this domain only: DESUGAR it to
    the six primitives (with the mapping and what is lost), or DECLARE IT A RECORDED
    EXTENSION (with the law-1 record text that T-4952 carries into docs/strata/kernel.md).
    Nothing in this domain is deleted -- T-4678 decided the delete list is empty.'
  evidence: []
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
DECISION-TURNED-LEAF under T-4681 (SF-21). One of eight, one per kernel-extension
domain the keyword audit identified. The owner has decided the FRAME; this leaf
decides the domain.

THE FRAME (T-4681, owner, 2026-09-19): docs/strata/kernel.md IS the spec. A
keyword that produces facts no primitive owns is NOT deleted -- it is wired into
the kernel deliberately, with a law-1 record. Governing rule: **"err on the side
of adding capabilities; we originally had a good idea and then forgot to
implement it."**

THE MEASUREMENT (scratchpad/STRATA-KEYWORDS.md): roughly **79 of 139 keywords
are not sugar** over the six primitives, spanning EIGHT domains -- code binding,
capability via-lists, waivers, entity/architecture, vmodel, policy, host/ACL,
kerberos. kernel.md:29 currently claims, falsely, "no other kernel extension
exists or is planned" (T-4952 corrects the doc).

THE DECISION THIS LEAF MUST RECORD, for its own domain only:
**either** desugar the domain to the six primitives (Node, Flow, Boundary,
Bound, Claim, Scenario), **or** declare it a RECORDED EXTENSION with a law-1
record.

Charter law 1 is "the prover never learns a domain word". The audit's test for
law-1-bearing: the elaborator does NOT desugar the construct into the six
primitives but instead hands a new field to the prover or to a Python-side
evaluator that is not the Datalog closure. Removing or re-siting such a
construct changes what the kernel can conclude -- which is why this is a
decision and not a refactor.

DELIVERABLE: the decision recorded in this body, plus -- if "recorded extension"
-- the law-1 record text that T-4952 will carry into kernel.md, and -- if
"desugar" -- the mapping from the domain's constructs onto the six primitives
and what is lost.

BLOCKED BY the module-system story (T-draft-0a0c7b43): per-module contracts
change what several of these domains must express, so deciding against today's
monolith would be deciding against a moving target.

NOT IN SCOPE: deleting anything. T-4678 decided the delete list is empty.

## THIS LEAF: host/ACL (`runs_as`/`unit`/`owns`/`listens`/`group`/`sudoers`/`platform`/`service_account`/`gmsa`/`service`/`acl`/`pipe`/`bin_path`/`managed`) -- _host.py plus _host_isolation*.py, HOST001/HOST002. Note the audit subtlety: _elaborate.py encodes several of these as NODE ATTRS (is_unit, owns), so they ride inside a primitive attribute bag, yet HOST001/002 are Python joins rather than Datalog -- so the desugar-or-extension question here is genuinely open.
