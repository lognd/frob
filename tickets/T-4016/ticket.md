---
id: T-4016
title: 'F-230: the TS walker emits no symbol for describe()/it() call expressions,
  so no frob:tests directive can ever bind a vitest test (root cause of F-172/F-219/F-225)'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/_walk_typescript.py
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
Consumer logand.app-v2 F-230, 2026-09-06. THIS IS THE ROOT CAUSE BEHIND F-172,
F-219 AND F-225, and it is verified in our own source.

THEIR CLAIM: "frob.lang._walk_typescript never yields a RawSymbol for a
describe/it call expression; the directive's enclosing/following lookup falls
through to the bare file path, which never matches a vitest node id."

VERIFIED, NOT ACCEPTED ON REPORT:

    git grep -c "call_expression" -- src/frob/lang/_walk_typescript.py  ->  0

The walker emits RawSymbols for `function_declaration` (:43), class-member
methods (:83) and top-level `lexical_declaration` constants (:107). It has NO
call-expression handling at all. `describe(...)` and `it(...)` ARE call
expressions. So a `frob:tests` directive written above an `it()` has no
enclosing symbol to attach to, and the edge degrades to the bare file path --
which can never equal a vitest node id of the form
`path::describe title > it title`.

THIS SUPERSEDES MY OWN OPEN HYPOTHESIS ON T-4003. I had recorded the TEST002/
TEST003 zeros as a possible cache/invalidation problem, having verified that all
three collectors ARE called (gates/__init__.py:6367-6384) and that TS was
deliberately admitted by T-0730. Both of those observations were correct and
neither was the answer: COLLECTION works, and the collected ids are fine. What is
missing is the OTHER side of the edge -- the graph has no symbol for the test, so
there is nothing to match the collected id against. Update T-4003 to point here
rather than continuing to chase the cache.

IT ALSO EXPLAINS WHY THE SYMPTOM SPANS TWO SYMBOL CLASSES. F-219 reported .tsx
components and F-225 reported plain .ts script entry points. Both are explained
at once: the failure is not in the subject being documented, it is in the TEST
symbol the directive must resolve to, which is absent for every vitest test in
every TS file.

THE FIX THEY PROPOSE IS THE RIGHT ONE: treat `it("<title>")` / `test("<title>")`
calls as test symbols named by their title, joined with enclosing `describe`
titles -- producing exactly the ids `.frob/vitest-collect.json` already holds. The
two sides then meet by construction rather than by coincidence.

CONSTRAINTS WORTH STATING BEFORE SOMEONE STARTS:
  - MATCH THE COLLECTOR'S ID FORMAT EXACTLY. `collect_ts_tests`'s own
    `_vitest_node_id` already defines the shape; derive the walker's symbol name
    from that definition rather than re-deriving the join separator and quoting
    by hand. Two independent spellings of one id format is precisely the desync
    that produces this class of bug.
  - HANDLE THE VARIANTS DELIBERATELY: `it`, `test`, `it.each`, `describe.skip`,
    `it.only`, template-literal titles, and titles containing the separator. Say
    which are supported and which are not, rather than silently covering the
    easy ones -- a partially-supported id format is a new silent zero.
  - A DYNAMIC TITLE (a variable, an interpolation) cannot be resolved statically.
    That case must be reported as unresolvable, NOT silently omitted, or it
    reintroduces the same invisible gap one level down.

CROSS-REFERENCES, all confirmed distinct from this and from each other:
  - T-3937/T-3925 fixed evidence BINDING to consult all collectors. Real fix,
    different path, already landed.
  - T-4003 (F-219/F-225) is the TEST002/TEST003 symptom -- likely resolved by
    this, but keep it open until measured.
  - T-3933 records that vitest EXECUTION is still unproven (its test uses a
    synthetic lambda). This ticket does not address that.

THEIR SECOND NOTE, worth carrying: "the installed 0.530.0 lacks the
quoted-positional-target parsing present in the frob checkout, so the alternate
convention cannot be used either (version skew)". That is T-4001 -- two builds
presenting the same version string -- biting the same user a second time, and it
is why they had no workaround available.

MUST-FIRE FIXTURE: a frob:tests directive above an `it()` binds to the vitest
node id that `collect_ts_tests` reports for that test.
MUST-STAY-QUIET: a TS file with no tests produces no spurious test symbols.
THIRD FIXTURE: a dynamically-titled test is reported as unresolvable rather than
silently skipped.
FOURTH FIXTURE: the walker's generated id and the collector's id agree for a
nested describe/it pair -- the desync, made checkable.

ACCEPTANCE
- Call-expression test symbols emitted, named from the collector's own id
  definition.
- Variant coverage stated explicitly.
- Dynamic titles surfaced, not dropped.
- T-4003 re-measured against this fix before it is closed.
- All four fixtures committed.