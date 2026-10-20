+++
id = "01M1T07P0KVNA0Z32WEA6B2MNZ"
title = "H3-7: a route returning a dict literal with no response model is invisible to every reference gate"
type = "bug"
category = "done"
outcome = "done"
priority = "critical"
parent = "01M1T07P0DHR8Z9D3E3PRGDJ7B"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-09-06T00:00:02Z"
aliases = ["T-4115"]
labels = ["milestone:1.1.0"]
scope = ["src/frob/gates/_route_response_model.py", "tests/gates_suite/test_route_response_model.py", "docs/modules/gate-route-response-model.md"]
+++

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
