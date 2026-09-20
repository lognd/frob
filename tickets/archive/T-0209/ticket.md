---
id: T-0209
title: capability scanner matches needles inside comments and strings
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability.py
- src/frob/lang/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_python.py'
  actor: logan
  at: '2026-09-19'
  old_length: 1001
  new_length: 5702
evidence:
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_comment_only_needle_does_not_fire
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_real_code_needle_still_fires_alongside_comment
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_string_literal_needle_still_fires
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_capability_module_self_scan_documented_false_positive
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_re_compile_alone_does_not_report_eval
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_bare_compile_call_still_reports_eval
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_genuine_eval_still_detected
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_scan_directory_capabilities_excludes_own_module
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 aprog-public: SYS100 reported capability net observed at assignments/api-harvester/assets/starter.py:22 -- that line is COMMENT text describing requests.get; the assignment forbids real network imports. Forced a false may declaration dragging bogus CWE-918 obligations -- corrupts the security posture the model attests (medium-high). Fix: consult tree-sitter comment/string spans (already produced by frob.lang) before substring matching; needle hits fully inside comment spans are dropped (string literals are subtler -- keep string hits for languages where code-in-string is an exec vector, e.g. eval payloads, but drop pure-comment hits everywhere). Litmus: comment-only fixture must NOT fire; code fixture still fires; the T-0151/T-0201 self-match tests stay green. Note duplicate-line issue too: the same site was reported twice (pilot gap 12) -- dedupe observations by (file,line,kind) while in there.

T-4718 sweep (condensed from src/frob/vet/_capability_python.py:36-102,
trimmed for DOCARCH002's 12-line cap): the trimmed block's full original
text, kept verbatim below.

# T-0328: import/binding-aware resolution for Python, the priority language
# (highest coverage). The plain substring scan above is EVADED by ordinary
# aliasing/from-import Python -- `import subprocess as sp; sp.run(x)` never
# contains the literal text "subprocess.run(" the needle table looks for,
# and `from os import system as e; e(x)` contains neither "os.system(" nor
# "eval(", so the scanner observes NOTHING even though the code genuinely
# execs. This block builds a per-file IMPORT/BINDING TABLE from the same
# tree-sitter parse `_comment_byte_spans` already uses, resolves each
# call/attribute site's leftmost name through it (reconstructing the
# fully-qualified target, e.g. `sp.run` -> `subprocess.run`), and re-checks
# the SAME needle tables against the RESOLVED identity string instead of
# raw source text -- no new registry field, no new needle vocabulary, just
# a second pass over a synthesized "what this call/attribute actually
# refers to" string. Every resolved match is still confirmed against
# `comment_spans` before counting (T-0209 posture unchanged).
#
# Scope-awareness (mandatory to avoid FALSE POSITIVES): a LOCAL binding --
# a function/method parameter, an assignment target, a `for`/`with ... as`
# target, or a nested `def`/`class` name -- SHADOWS an import of the same
# name in every enclosing scope from the site up to module level. `def
# g(system): system(x)` (param) and `class Job: def run(self): ...` then
# `Job().run()` (method access on an unrelated object) must NOT resolve to
# `os.system`/a dangerous `run`, because the leftmost name in each case
# either resolves to a local binding (shadowed) or to an expression this
# resolver deliberately does not chase further (a `call` node, e.g.
# `Job()`, is not a resolvable "object" for attribute-chain purposes, so
# `Job().run` never reaches the import table at all).
#
# Known limitations, documented rather than silently eaten (mirrors this
# module's existing "Honest limits" posture): `from X import *` adds no
# binding (a star-imported name is untraceable without also modeling X's
# own exports); a function-scoped `import` is folded into the SAME
# file-wide binding table as a module-level one (a narrow, safe-direction
# over-approximation -- it can only ADD a resolution, never suppress a
# real one); a relative import's dotted text (`from . import x`) is kept
# as literal text (`"..x"`-shaped), which will not coincidentally collide
# with any real registry needle in practice. TS/C-C++ are OUT of scope for
# this pass -- C/C++'s `#include` is coarse-only by design (module
# docstring), and TS's binding table is noted as follow-up work, not
# attempted here. Rust gets its own binding-aware pass, T-0378 below.
#
# T-1626: two evasions the T-0328 resolver used to miss silently (the
# ticket's own worked examples) are now resolved rather than dropped:
# `functools.partial(dangerous, ...)` (`_resolve_py_expr`'s `call` branch
# recognizes a resolved-`functools.partial` callee and resolves through to
# its first positional argument -- `p = functools.partial(os.system, cmd);
# p()` now resolves `p()` to `os.system`), and a literal-keyed dict/list
# dispatch (`_record_py_dict_container_alias`/`_record_py_list_container_
# alias` record one alias entry per literal key/index at assignment time,
# `_resolve_py_subscript` looks it up at the call site -- `funcs = {"run":
# subprocess.run}; funcs["run"](cmd)` now resolves). Both stayed
# genuinely silent before: a NON-literal key/index or a dynamically
# computed `getattr` name is a SEPARATE, already-covered case --
# `frob.gates._opaque`'s OPAQUE001 (`RUNTIME_OPAQUE_CONSTRUCTS`/
# `RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS`, `_capability_scan.py`) already
# fires fail-closed on those (non-literal subscript-then-call, bare
# `getattr(`/`setattr(`/`eval(`/`exec(`/`__import__(`) -- this module
# only had to close the LITERAL-key gap OPAQUE001 explicitly defers to
# "the ordinary resolver's job" (`_subscript_key_looks_literal`'s
# docstring) but the ordinary resolver never actually implemented until
# now, which meant a literal-keyed dict/list dispatch fell through BOTH
# mechanisms: too resolvable to trip OPAQUE001, never actually resolved
# by this module. Cross-file wrapper attribution (a helper in another
# module forwarding to a dangerous callable) is NOT attempted here -- it
# needs `frob.graph.callgraph`-backed cross-file call resolution, a
# larger, separate unit of work; see T-1626's Done report / follow-up
# ticket for the split.