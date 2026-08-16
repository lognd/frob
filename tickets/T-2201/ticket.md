---
id: T-2201
title: 'T-2114''s pre-land gate detects frob: directives by substring matching block_text,
  the same lexical question T-2183 just fixed with grammar-parsed comment nodes, and
  its family list is hardcoded to COV001/TEST001'
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: T-1662
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'Measured at src/frob/app/ticket_runner/_land_cmd.py:3311-3312, the gate decides
    with: has_doc = ''frob:doc'' in block_text or ''frob:waive COV001'' in block_text;
    has_tests = ''frob:tests'' in block_text or ''frob:waive TEST001'' in block_text.
    Substring matching, so a directive-looking string inside a docstring or string
    literal satisfies the gate and a real directive written in an unexpected position
    is missed. T-2183 landed hours earlier (e5a297bf88e9) answering the identical
    question -- ''is this line a genuine frob: directive?'' -- with frob.lang.raw_tree/COMMENT_TYPES
    placing the line inside a real grammar COMMENT node, deliberately excluding docstrings.
    Reuse that machinery. This test MUST fail against current main: a new public symbol
    whose ONLY ''frob:doc'' text sits inside a docstring or string literal must NOT
    satisfy the gate.'
  evidence: []
- text: 'The family list is hardcoded, and this is the THIRD instance of one-family-at-a-time:
    T-1907 gated the type family, T-2114 generalised its shape to COV001/TEST001,
    and the ARCH/lint families still accumulate per land -- measured now at ARCH001
    4, ARCH103 1, E501 1, PERF004 1 on the unscoped floor, up from 8 code errors earlier
    today to 15. Parameterise the gate over the families a diff can introduce rather
    than adding a third hardcoded pair; otherwise the next family repeats this ticket.'
  evidence: []
- text: 'Do NOT fix the substring check by making the pattern stricter (anchoring,
    requiring a leading ''#''). T-2183 already proved that shape wrong: its occurrence
    2 was a genuinely comment-positioned directive inside a docstring, which no pattern
    tightening separates -- the question is whether the GRAMMAR says the line is a
    comment, not what the text looks like. Do NOT reintroduce a full unscoped frob
    check at land time either; that is the ~208s cost T-1684 deliberately removed
    and T-2114 correctly avoided by working from the diff alone.'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
