---
id: T-0127
title: 'DOC002-style gate: validate frob:doc anchors resolve to real doc slugs'
state: done
kind: feature
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestDocanchorGate::test_unresolvable_anchor_fires
designated_repro_test: null
threat: null
component: null
---
Found during T-0126 review: frob:doc directives can target heading slugs that do not exist (e.g. docs/strata/evidence.md#the-enables-cascade vs the real slug #the-enables-cascade-soundness-dependencies-mechanized from '## The enables cascade (soundness dependencies, mechanized)'). No gate validates that a frob:doc target file+slug resolves (_slugify exists in src/frob/graph/dsl.py). Add a gate that parses doc targets, slugifies headings in the target file, and errors/warns on unresolvable anchors. Several pre-existing broken anchors in strata/_packs.py and _claims.py will surface -- fix them in the same change.
## Done report

DOC002 (gate name docanchor, ERROR per DOC001 precedent): every
frob:doc target must resolve to a real heading slug (graph slugify,
now public) or an explicit <a id> anchor in the target file;
unreadable files and missing fragments fire rather than silently
passing. Running the gate surfaced 39 genuinely broken anchors, all
fixed in the same change: evidence.md heading shortened to match its
cited slug, five docs/commands pages gained real Public API sections
(26 directives), fuzz.md got an explicit anchor, and frob.docs's seven
directives were corrected. Zero DOC002 violations repo-wide at close.
Reviewer APPROVED; verified at merge: 149 gates+graph tests green.