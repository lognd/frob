# Route response model gate

### ROUTE001 (T-4115)

<!-- frob:describes src/frob/gates/_route_response_model.py::route_response_model_gate -->

`frob.gates._route_response_model` -- `route_response_model_gate` (gate
name `route_response_model`, WARN severity, waivable). F-307 H3-7:
COV/WIRE reference gates see a response-model class as referenced once
any route uses it, so a route that returns a bare `dict` literal instead
of that model is invisible to every reference gate -- there is no
missing reference to notice, because the route never referenced a
response model at all. This is the same family as an existing
guard-inventory check: "build an inventory of every X and flag the ones
missing Y" -- here, X is every decorated route function, Y is a response
model on its return.

`route_response_model_gate` enumerates every function decorated with a
configurable route-decorator pattern (any decorator whose attribute name
is one of the conventional HTTP verbs -- `get`, `post`, `put`, `patch`,
`delete` -- called as `@<anything>.<verb>(...)`; not hardcoded to one
web framework's exact decorator import, since frob itself defines no
HTTP routes to anchor a hardcoded pattern against) whose body returns a
bare `dict` display (`return {...}`) rather than an instantiated typed
object.

Scoped precisely to a bare dict literal in source, not every dict-shaped
return value:

  - `return StatusResponse(...)` (a call, not a dict display) never
    fires.
  - `return {**model.model_dump()}` (a dict display whose ONLY content
    is a double-starred unpack of a typed-looking expression) is treated
    as derived from a typed object, not a raw literal, and does NOT
    fire.
  - `return {**model.model_dump(), "extra": 1}` (a dict display that
    mixes an unpack with a literal key/value pair) still contains an
    un-typed literal pair -- the exact surface this rule exists to
    catch -- and DOES fire.

Waivable with the standard file-scoped `frob:waive ROUTE001
reason="..."` directive, for a route deliberately without a response
model.

## Rule table entry

| Rule | Gate name | Meaning |
| --- | --- | --- |
| ROUTE001 | route_response_model | (warn) a route-decorated function (`@<obj>.get/post/put/patch/delete(...)`) returns a bare dict literal with no declared response model -- see "ROUTE001 (T-4115)" above |
