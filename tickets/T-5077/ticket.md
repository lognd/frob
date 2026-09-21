---
id: T-5077
title: 'DECISION: kernel extension domain 5/8 -- vmodel (vmodel_node/vmodel_edge/kind/level/runnable/code_ref/src/dst),
  the family used only in consumer designs: desugar to the six primitives, or record
  as an extension?'
state: queued
kind: docs
origin: agent
created: '2026-09-19'
priority: medium
blocked_by:
- T-5081
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

BLOCKED BY the module-system story (T-5081): per-module contracts
change what several of these domains must express, so deciding against today's
monolith would be deciding against a moving target.

NOT IN SCOPE: deleting anything. T-4678 decided the delete list is empty.

## THIS LEAF: vmodel (`vmodel_node`/`vmodel_edge`/`kind`/`level`/`runnable`/`code_ref`/`src`/`dst`) -- gates/_vmodel.py:159-162, an entirely separate spec graph. grammar_core.rs:76-92 says so explicitly: "new, independent top-level statement kinds". NOTE: this is the domain T-4678 correction 2 nearly had deleted -- the vmodel family is used ONLY in consumer designs (vmodel.strata alone: kind x1292, dst x764, runnable x269, code_ref x259) and appears nowhere in frob own designs.
