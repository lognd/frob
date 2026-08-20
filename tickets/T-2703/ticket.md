---
id: T-2703
title: DOC006 scans inline code spans, reading C++ lambda captures as TOML section
  keys (72 false positives downstream)
state: queued
kind: bug
origin: human
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by a downstream consumer repo (aprog-public) running frob 0.530.0
on 2026-08-20. 72 of that repo's 87 DOC errors are this one false positive.

## Symptom

DOC006 flags `[x]` and `[...]` inside INLINE CODE SPANS in prose as
unresolved frob.toml/pyproject.toml section keys.

`activities/callable-lineup/README.md:35`:

    Capturing a variable **by value** (`[x]`) takes a frozen private copy

`[x]` there is a C++ lambda capture clause inside backticks, not a TOML
section header. All 72 hits are prose about C++ lambdas and slicing.

## Verified in code

DOC006 is emitted from `src/frob/gates/_docptr.py:725`. That module has
ZERO references to `strip_code_spans` -- confirmed by grep. Meanwhile
`src/frob/gates/_doclink_docanchor.py` imports it (line 38) and applies it
in two scans (lines 260, 551) for DOC008/DOC011.

NOTE: the original report guessed DOC006 lived in `_doclink_docanchor.py`.
It does not -- it is in `_docptr.py`. The fix belongs there.

## Fix direction

Run DOC006's scan over `strip_code_spans(text)`, the shared helper in
`frob.gates._markdown_scan` (T-1486/T-1700) that DOC008 and DOC011 already
use. Do NOT write a second stripper -- the helper exists precisely so a
second prose-scanning rule never has to reimplement it.

A bare `[x]` OUTSIDE a code span may still be worth flagging; only the
code span should be inert.

## Positive controls, both directions

- `[x]` inside a backtick code span must NOT fire
- a genuinely unresolved `[section.key]` pointer in plain prose must STILL
  fire -- without this the fix is indistinguishable from disabling DOC006
- a fenced code block must remain inert (existing behavior, do not regress)
