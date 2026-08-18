---
id: T-2470
title: 'C++ ARCH symref producer spells qualnames with :: instead of frob''s canonical
  . join'
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/lang/_common.py
- src/frob/arch/_cpp.py
- src/frob/arch/_cpp_mayraise.py
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
found while working T-2438 (a symbol-bound frob:waive silently failed to
match when symrefs differ, with no fallback and no diagnostic).

Root cause of the confirmed live repro: frob.lang._common._cpp_class_methods
(shared by frob.arch._cpp/_check_long_functions and frob.arch._cpp_mayraise)
builds a C++ method's qualname with the language's own native scope
operator: f"{class_name}::{method_name}" -- e.g. "Foo::bar". That string
is used BOTH for the human-facing message text (where "::" is idiomatic
and correct) AND as the Violation.symref fed to frob.gates._waive's
matcher.

Every other symref producer -- and the DSL/graph symbol table that binds
a symbol-bound frob:waive comment to its nearest enclosing symbol
(frob.lang._walk_c, which builds RawSymbol.qualname via ".".join(...))
-- uses "." as the canonical qualname join character. So for the same
C++ method, violation.symref reads "<path>::Foo::bar" while the waiver
comment binds to "<path>::Foo.bar" -- two different strings for the same
symbol, which never compared equal.

Reproduced directly (both strings printed side by side):
  frob.arch._cpp._check_long_functions(...) -> symref='<path>::Foo::bar'
  frob.lang.parse_file + frob.graph.dsl.parse_directives on the same
    source, with a symbol-bound frob:waive comment above `bar` -> Edge.src
    == '<path>::Foo.bar'

T-2438 hardened the CONSUMER side (frob.gates._waive._match_waiver now
normalizes '::' -> '.' before comparing, plus a loud diagnostic on a
genuine remaining mismatch) as a stopgap within its own declared scope
(src/frob/gates/_waive.py only). That consumer-side normalization is
inherently a workaround, per this repo's own precedent (T-2314 fixed the
exact same shape of bug -- absolute vs relative PERF paths -- by
normalizing at the PRODUCER's boundary, not by teaching every consumer
both spellings).

The real fix: give frob.lang._common._cpp_class_methods (or its callers)
a SEPARATE canonical-dot-joined qualname for the symref= it feeds
Violation(...), while keeping the "::"-spelled name only in the
human-facing message= text C++ readers expect. This should also cover
frob.dup._legacy if it independently reconstructs a symref from the same
shared helper for anything compared against a waiver.

Positive controls for the fix: a frob:waive ARCH001 (or any other
symref-carrying C++ rule) bound to a class method must waive its finding
using ONLY the dot-joined symref -- i.e. the T-2438 consumer-side
normalization becomes provably unnecessary for this producer once fixed
(though it should stay, as defense in depth for any OTHER producer with
the same disease not yet found).