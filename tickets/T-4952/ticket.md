---
id: T-4952
title: kernel.md:29 claims no other kernel extension exists or is planned; eight domains
  and ~79 non-sugar keywords say otherwise
state: done
kind: docs
origin: agent
created: '2026-09-19'
priority: high
parent: T-4681
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/strata/kernel.md
- tests/unit/strata/test_kernel_doc_extensions.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/strata/test_kernel_doc_extensions.py::test_law_one_record_present_for_each_domain
- tests/unit/strata/test_kernel_doc_extensions.py::test_all_eight_extension_domains_are_named
- tests/unit/strata/test_kernel_doc_extensions.py::test_false_no_other_extension_claim_is_gone
designated_repro_test: null
acceptance:
- text: Given docs/strata/kernel.md:29 states verbatim 'no other kernel extension
    exists or is planned' while the keyword audit measured ~79 of 139 keywords as
    non-sugar across eight domains (code binding, capability via-lists, waivers, entity/architecture,
    vmodel, policy, host/ACL, kerberos), when this lands, then that sentence is gone
    and all eight domains are named as deliberate extensions -- a docs check that
    fails at HEAD c8f56ef10.
  evidence:
  - tests/unit/strata/test_kernel_doc_extensions.py::test_law_one_record_present_for_each_domain
  - tests/unit/strata/test_kernel_doc_extensions.py::test_false_no_other_extension_claim_is_gone
- text: 'Given charter law 1 is ''the prover never learns a domain word'', when each
    domain is named, then it carries a law-1 record stating what crosses into the
    prover and what stays Python-side, using the audit''s test: law-1-bearing means
    the elaborator does not desugar it into the six primitives.'
  evidence:
  - tests/unit/strata/test_kernel_doc_extensions.py::test_all_eight_extension_domains_are_named
  - tests/unit/strata/test_kernel_doc_extensions.py::test_law_one_record_present_for_each_domain
- text: Given whether each domain should be desugared or declared a recorded extension
    is one decision per domain blocked by the module-system story, when this lands,
    then it documents the eight domains AS THEY ARE today and pre-empts none of those
    decisions.
  evidence:
  - tests/unit/strata/test_kernel_doc_extensions.py::test_all_eight_extension_domains_are_named
  - tests/unit/strata/test_kernel_doc_extensions.py::test_false_no_other_extension_claim_is_gone
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
Docs leaf under T-4681 (SF-21). Story points: 2.
IMMEDIATELY DISPATCHABLE -- no blockers. It does NOT wait on the module system:
the sentence being corrected is false today.

THE FALSE CLAIM, planter-verified verbatim at HEAD, docs/strata/kernel.md:29:

    reduce to this; no other kernel extension exists or is planned.

THE MEASURED COUNTER-EVIDENCE (scratchpad/STRATA-KEYWORDS.md, 139 keyword rows):
roughly **79 of 139 keywords are not sugar** over the six primitives. They span
**eight domains** the six-primitive charter does not cover:

1. code binding (`code`) -- _code_binding.py; the tier-2 SYS100-103 surface.
2. capability via-lists (`may`/`via`/`of`/`exclusive`) -- _effects.py; kernel.md:13
   lists the `may` set but NOT via-lists or exclusivity, which SYS111 reads.
3. waivers (`waive`/`reason`/`ticket`) -- _waive.py; meta-facts about findings.
4. entity/architecture (`entity`/`architecture`/`obligation`/`binds`/
   `configuration`) -- _design_load.py:289,374-429; SYS300-303 refuse structurally
   at parse/load time, not by Datalog.
5. vmodel (`vmodel_node`/`vmodel_edge`/`kind`/`level`/`runnable`/`code_ref`/
   `src`/`dst`) -- gates/_vmodel.py; grammar_core.rs:76-92 calls them "new,
   independent top-level statement kinds".
6. policy (`policy`/`forbid`/`confine`/`mediate`/`require`/`call`/`import`) --
   _policy.py; lexical/AST rules over source under a refinement-monotonicity
   checker.
7. host/ACL (`runs_as`/`unit`/`owns`/`listens`/`acl`/`sudoers`/...) -- _host.py,
   _host_isolation*.py; HOST001/002 are Python joins.
8. kerberos (`realm`/`kdc`/`spn`/`delegation`/`trusts`/...) -- _krb.py; a third
   graph beside Node/Flow and vmodel.

THE AUDIT'S FRAMING, which this rewrite must preserve: kernel.md's "six
primitives" is **accurate about the PROVER's fact language and misleading about
the SURFACE language**. The six primitives are not wrong and are not being
demoted -- T-4681's decision keeps kernel.md as the SPEC. What is wrong is the
denial that anything else exists.

WHAT TO WRITE
Rewrite docs/strata/kernel.md so that it:
- keeps the six primitives as the prover's fact language, stated as such;
- names the eight domains above as DELIBERATE extensions rather than drift;
- carries a **law-1 record per domain**: charter law 1 is "the prover never
  learns a domain word", so for each domain state explicitly what crosses into
  the prover and what stays Python-side. The audit's definition is the test: a
  keyword is law-1-bearing when the elaborator does NOT desugar it into the six
  primitives but hands a new field to the prover or to a non-Datalog evaluator.
- deletes the false sentence at line 29 and replaces it with an accurate one.

SCOPE NOTE: this leaf writes documentation only. Whether each domain SHOULD be
desugared to the six primitives or stay a recorded extension is NOT decided
here -- that is one decision-turned-leaf per domain, blocked by the module-system
story, tracked on T-4681. Write the eight domains as they ARE today; do not
pre-empt those eight decisions.

Also correct, while here, the framing SF-21 originally flagged: kernel.md's own
later sections (age, capacity, demand, growth-rate, scenario, verdict,
assumption ledger, prover pipeline) run 761 lines, so the "six primitives"
headline already survives only in the headline.

POSITIVE CONTROL (the check that fails today)
A docs test asserting docs/strata/kernel.md contains no sentence claiming no
other kernel extension exists, and that it names all eight domains. It fails at
HEAD c8f56ef10 on line 29. Per memory/catalogued-is-not-enforced.md, naming the
domains in prose is not the same as enforcing them -- so this leaf's deliverable
is the corrected doc plus that standing check, not a promise to keep it current.