---
id: T-4115
title: 'H3-7: a route returning a dict literal with no response model is invisible
  to every reference gate'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: critical
parent: T-4109
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_route_response_model.py
- tests/gates_suite/test_route_response_model.py
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
F-307 H3-7 (verbatim, quoted at the bottom of T-4109's body). COV/WIRE gates
see a response model class (StatusResponse-shaped) as referenced once three
routes use it, so no gate notices the four routes that return a bare dict
literal instead of that model -- a gap only visible today by reading a
docstring against the decorators by hand. Proposed rule, in the same family
as an existing guard-inventory check (SIT-011 in the consumer's own repo,
which frob does not have -- the FAMILY is "build an inventory of every X and
flag the ones missing Y", not a specific rule to port): every route
returning a dict literal has a response_model.

Work:
- an AST-level route inventory: for a given route-decorator convention
  (must be CONFIGURABLE -- e.g. a decorator name pattern like
  @*.get/@*.post, not hardcoded to one specific framework's exact import
  path, since frob itself has no web framework to anchor a hardcoded
  pattern against) find every decorated route function whose body's return
  statement(s) construct a dict literal directly (return {...}) rather than
  an instantiated model/typed object
- flag each such route as missing a response model (WARN-tier, waivable)
- must not false-fire on a route that returns a dict literal produced by
  calling a typed constructor/serializer (model.model_dump()-shaped) --
  scope this precisely: the concern is a BARE dict literal in source, not
  every dict-shaped return value

Fixture note: this concerns a route-decorator/response-model shape frob's
own tree does not have (frob is a CLI, not a web backend). Build a small
synthetic fixture package (a handful of files under the test directory
only) with fake route decorators and functions, with:
- must-fire: a decorated route function whose body does `return {"status":
  "ok"}` directly
- must-stay-quiet: a decorated route function that does `return
  StatusResponse(status="ok")` (a typed constructor, not a bare dict)
- third: a decorated route function that returns a dict literal built by
  unpacking a typed object (return {**model.model_dump()}) -- decide and
  document whether this should fire or not (it is dict-shaped in source but
  derived from a typed model), rather than leaving the boundary implicit
FLAG EXPLICITLY in the Done report that the fixture is synthetic, not drawn
from frob's own dogfood surface -- frob defines no HTTP routes of its own.

frob:ticket T-4109