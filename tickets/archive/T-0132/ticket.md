---
id: T-0132
title: 'strata surface grammar: code=<glob>/may <capability> unreachable from .strata
  source text'
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- strata-core/src/parse.rs
- src/frob/strata/_ast.py
- src/frob/strata/_elaborate.py
- docs/strata/surface.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_parse.py::TestParseModule::test_parses_node_code_globs_and_may_capabilities
designated_repro_test: null
threat: null
component: null
---
Found while writing design/frob.strata (T-0081, self-hosting phase-4 exit).

strata-core's lexer only accepts [A-Za-z_][A-Za-z0-9_]* for IDENT
(is_ident_start/is_ident_cont, strata-core/src/parse.rs), and parse_node's
`attr KEY=VAL` requires VAL to be exactly one IDENT token (parse_attrval).
There is no STRING- or glob-valued attr anywhere in the surface grammar.

This means two tier-2 features that already have full Python
implementations and test suites are completely unreachable from `.strata`
source text:

- `code=<glob>` (T-0078, docs/strata/surface.md#code-binding-tier-2-v0-
  implementation) -- a glob like `src/frob/app/**` cannot be lexed; every
  test exercising bind_code/check_import_conformance builds a KernelModel
  directly in Python (tests/unit/strata/test_code_binding.py).
- `may <capability>` (T-0079) -- same story; the `component` decl that
  would host `may` per the grammar sketch
  (docs/strata/surface.md's `comp_item := ... | "may" capability`) is not
  even parsed (`parse_component` does not exist in strata-core/src/parse.rs
  outside the policy scope-spec use of the `component` keyword).

design/frob.strata (T-0081) documents each component's real code
ownership as an informal comment instead of a `code=` attr, and omits
`may` capabilities entirely, because the grammar cannot express either
today. Fix: extend the lexer with a STRING token (or a glob-safe IDENT
extension allowing `/`, `*`, `.`) and wire `code`/`may` into `parse_node`
(or the `component` decl), then update design/frob.strata to use the real
syntax and drop this ticket's workaround comment.