---
id: T-4090
title: 'H3-1b: TS frob:invariant positive control for throw-safe re-arm loops'
state: queued
kind: invariant
origin: agent
created: '2026-09-06'
priority: high
parent: T-4089
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_inv.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given an experiment binding a frob:invariant directive on a TS function to
    a vitest test whose callback throws, when it is run against frob itself, then
    the result confirms whether the bind-and-verify cycle already works end-to-end,
    before any code change
  evidence: []
- text: given the experiment confirms clean, when this ticket closes, then the createSharedFrameLoop
    shape is recorded as a positive worked example for docstring-claims-as-obligations
    authors
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
H3-1's second half (F-296), FILED FIRST per the coordinator's instruction as the cheapest concrete obligation in this list. The consumer's own words: a missing frob:invariant on createSharedFrameLoop stating "the RAF chain re-arms on every tick regardless of what a subscriber does," with evidence bound to a test whose subscriber throws.

VERIFIED: this needs NO NEW RULE KIND -- frob:invariant (INV001/INV002, src/frob/gates/_inv.py) and TS-language directive/comment parsing already exist generically (the TS walker's comment-token extraction feeds the same directive DSL every language uses, per src/frob/graph/dsl.py). git grep found no existing regression/positive-control fixture in frob's OWN test suite proving an end-to-end TS-side frob:invariant bind-and-verify cycle for this exact shape (evidence = a test whose assertion is that a THROW inside a callback does not break an enclosing re-arm/retry loop). So this is not a capability gap, it is an UNPROVEN CAPABILITY -- the mechanism should already work, but nothing in frob's own suite demonstrates it working for a throw-based TS test, which is exactly the gap that let this consumer finding go unclaimed by any existing obligation.

WORK: (1) confirm (via a small experiment against frob itself, not the consumer repo) that a frob:invariant directive placed on a TS function, with evidence bound to a vitest test whose callback throws, is correctly extracted, bound, and verified by frob check -- no code change expected if this confirms clean. (2) if it confirms clean, this ticket's remaining scope is authoring guidance/documentation: this exact defect shape (a subscriber's throw silently killing an enclosing scheduler loop) is a good addition to whatever example catalogue frob ships for frob:invariant authors, since "the loop keeps re-arming regardless of subscriber behavior" is a crisp, testable, non-keyword-inferred invariant statement -- a positive worked example for the docstring-claims-as-obligations family (T-3954) of what a GOOD frob:invariant looks like, in contrast to the vague keyword-based claims that family is otherwise fighting. (3) if step 1 finds an actual TS-binding defect, this ticket becomes the fix for that defect instead.

THE THEME THIS CHILD ALSO CARRIES, per the coordinator's explicit instruction: this round's structural pattern is a contract stated in PROSE and enforced on one side of an ABI/language boundary while unenforced on the other -- SYS-031 ("engine functions operate on caller-owned buffers with explicit cols/rows/count parameters") is enforced in Rust BY HAND and not at all in TypeScript; H3-3 (filed separately, this same epic) is the identical shape for a time/epoch contract. This child is the cheapest, most concrete instance of that theme: a scheduler-loop-robustness contract that already has a natural frob:invariant home and simply was never written down as one.
