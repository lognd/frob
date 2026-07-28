# strata boundaries -- the six-phase contract and outcome-conditioned frames

<!-- frob:ticket T-0048 -->

One sentence: a boundary is an operation whose phases each carry a frame
(what may be modified) and label rules (what may be read/emitted), and
"does not modify on failure" is the same frame machinery conditioned on
outcome -- one mechanism for both (T-0069).

## The six phases

```
boundary Ingress between Browser and Gateway {
  admit  { authn none; rate_limit 20/min per ip; max_size 64 KiB }
  parse  { accepts SignupForm strict; time linear; frame {} }
  judge  { endorses foreign -> authenticated when jwt_verified }
  effect { frame { SessionStore.write } }
  record { audit to AuditLog with trace_id }
  refuse { respond ErrorView : Public; frame { AuditLog.append } }
}
```

| Phase | Obligation | Vulnerability class killed |
|---|---|---|
| `admit` | resource decisions before interpretation: size caps, rate limits, authn precede parsing | zip bombs, slowloris, unauthenticated amplification |
| `parse` | parse-don't-validate: pure (`frame {}`), total, linear-time interpretation into a typed value | deserialization RCE, side-effects-during-validation, ReDoS |
| `judge` | the label/trust change itself, predicated; nothing before this line has written anything | effects before endorsement |
| `effect` | first phase with a real frame, and only the declared one | scope creep of boundary side effects |
| `record` | audit emit per `std.policy.observe`; boundary crossings are a mandatory log class | undetectable crossings; feeds detection SLAs |
| `refuse` | failure frame is audit-append only; the error response is a labeled egress flow | refusal-as-write-primitive; stack-trace/info leaks (a label violation, caught by ordinary closure) |

Responses are boundaries too: a response body from an authenticated peer
is still foreign-influenced data (authenticating a peer does not endorse
its payload) and needs its own judge phase before reaching state.

## Frames and failure atomicity

```
operation Transfer on LedgerDb {
  modifies { Balance(from), Balance(to) } on Ok
  modifies {} on Err                       // the strong guarantee
  atomic via transaction LedgerDb
}
```

`modifies ... on Ok / on Err` are conditional flow permissions (the
kernel's only extension, `kernel.md`). Discharge, preferring the highest
rung (T-0075):

1. **Stage-then-commit (L5).** Fallible work touches only local/shadow
   state; an infallible atomic commit publishes. Because the frob graph
   knows which functions return Result, "this region calls nothing
   fallible" is decidable -- errors-as-values makes infallibility
   checkable. In-repo precedent: INV-001 (`os.replace` on frob.lock) is
   exactly this pattern.
2. **Immutable build-and-swap (L5).** New value constructed, published by
   single reference swap; old state untouched by construction.
3. **Transaction chokepoint (L4).** All writes through one tx handle, one
   transaction per operation, no writes outside -- confinement +
   chokepoint forms from `policy.md`; rollback is the store's proof.
4. **WAL / journal with idempotent replay.** Also the crash path: `atomic`
   composes with `on crash` contracts -- the commit must be atomic under
   crash too (rename, single COMMIT), and the recovery source's staleness
   bound is the operation's RPO.

**Cross-store refusal.** An `atomic` claim whose Ok-frame spans two stores
(or a store and an external service) is rejected at the type level unless
a coordinator is declared: declare `saga compensate ... within t` and
weaken to `reconciled within t`, or move the external call after commit.
Distributed atomicity by wishful thinking is a "not possible" diagnostic,
never a silent acceptance. Sagas carry their own obligations: the
compensating action is retried (at-least-once) and therefore must be
idempotent -- the standard delivery-semantics join applies.

**Generated fault injection (L2).** From every `modifies {} on Err` claim,
the exhaustive per-Err-variant injection tests of `evidence.md` are
generated mechanically.

## Crash contracts and error totality (adjacent claims)

- `errors total`: every declared error value consumed exhaustively (closed
  ErrorSet match, no discarded Result, variant liveness) -- see
  `std.policy.errors-total` in `policy.md` (T-0070).
- `panics contained by S`: every escape path terminates at the declared
  crash boundary; per-language chokepoints (excepthook, catch_unwind,
  uncaughtException, terminate handler, signal handlers).
- `on crash { restart within t; inflight fail retriable within t';
  state recovered from X }` desugars to an auto-generated crash scenario
  plus bounds. The no-hang check: every synchronous caller of a crashable
  component must declare a timeout compatible with the crash contract;
  crash + retry implies at-least-once, which demands idempotent effects
  downstream (T-0074).

  <!-- frob:invariant INV-027 -->

## v0 implementation

<!-- frob:ticket T-0069 -->
<!-- frob:ticket T-0070 -->

What compiles now (T-0069/T-0070): the boundary phase-block grammar, the
`operation` construct, and three node observability properties --
declared structure plus the structural diagnostics below. What does not
compile yet: fault-injection *generation* from `modifies {} on Err`
claims (L2, T-0075) and wiring the ERR/OBS gates into `frob check`
(phase 4) -- both out of scope here.

### Grammar (`strata-core/src/parse/mod.rs`)

```
phase_block := "{" admit? parse_phase? judge? effect? record? refuse? "}"
admit       := "admit" "{" ("rate_limit" QUANTITY | "max_size" QUANTITY)* "}"
parse_phase := "parse" "{" ("time" IDENT | "frame" "{" FRAMELIST? "}")* "}"
judge       := "judge" "{" "}"
effect      := "effect" "{" "frame" "{" FRAMELIST? "}" "}"
record      := "record" "{" "audit" "to" IDENT "}"
refuse      := "refuse" "{" "respond" IDENT (";" "frame" "{" FRAMELIST? "}")? "}"
FRAMETARGET := IDENT ["(" IDENT ")"]
FRAMELIST   := FRAMETARGET ("," FRAMETARGET)*

operation := "operation" IDENT "on" IDENT "{" operation_prop* "}"
operation_prop := "modifies" "{" FRAMELIST? "}" "on" IDENT | "atomic" "via" IDENT

node_prop  += "errors_total" | "panics_contained_by" IDENT | observe
observe    := "observe" "{" ("log" IDENT ("," IDENT)* | "to" IDENT)* "}"
```

A boundary's phase block is entirely optional (an unadorned `boundary ...`
statement still parses, `phases: null`); each of the six phase keywords
may appear at most once, a repeat being a parse error rather than
last-write-wins (charter law 2 -- silently dropping a declared phase is a
security-relevant default). `judge`'s block must be literally `{ }`;
`parse`'s `frame` is grammar-open (unlike the illustrative empty `frame
{}` in the phase table above) precisely so the elaborator's "must be
empty" rule below has a real violation to catch.

### AST (`src/frob/strata/_ast.py`)

<!-- frob:describes src/frob/strata/_ast.py::AdmitPhase -->
<!-- frob:describes src/frob/strata/_ast.py::ParsePhase -->
<!-- frob:describes src/frob/strata/_ast.py::EffectPhase -->
<!-- frob:describes src/frob/strata/_ast.py::RecordPhase -->
<!-- frob:describes src/frob/strata/_ast.py::RefusePhase -->
<!-- frob:describes src/frob/strata/_ast.py::PhaseBlock -->
<!-- frob:describes src/frob/strata/_ast.py::OperationDecl -->
<!-- frob:describes src/frob/strata/_ast.py::ObserveDecl -->

One frozen pydantic model per phase (`AdmitPhase`, `ParsePhase`,
`EffectPhase`, `RecordPhase`, `RefusePhase`), collected into `PhaseBlock`
and attached as `BoundaryDecl.phases: PhaseBlock | None`. `OperationDecl`
(`id`, `on`, `modifies_ok`, `modifies_err`, `atomic_via`) is a new
top-level `Module.operations` entry. `ObserveDecl` (`log`, `to`) attaches
as `NodeDecl.observe: ObserveDecl | None`, alongside the new
`NodeDecl.errors_total: bool` and `NodeDecl.panics_contained_by: str |
None` fields.

### Elaboration (`src/frob/strata/_elaborate.py`)

<!-- frob:describes src/frob/strata/_elaborate.py::_validate_boundary_phases -->
<!-- frob:describes src/frob/strata/_elaborate.py::_validate_operations -->
<!-- frob:describes src/frob/strata/_elaborate.py::_validate_observability -->
<!-- frob:describes src/frob/strata/_elaborate.py::_elaborate_boundary_phase_flows -->
<!-- frob:describes src/frob/strata/_elaborate.py::_elaborate_operation_flows -->
<!-- frob:describes src/frob/strata/_elaborate.py::_elaborate_observe_flows -->

Every rule below is a structural check purely against the parsed
`Module` (no dependency on the elaborated `KernelModel`, since every id
it needs -- node/store/cache/queue/cdn/balancer ids, `attrs` markers --
is already a plain field on some AST decl); all fail closed with a logged
`StrataError`, never a silent default (law 2):

- **Admit/parse frames must be empty.** A `parse` phase whose `frame`
  block names any entry is `FrameViolation` -- effects before endorsement
  is exactly the vulnerability class the six-phase contract exists to
  kill. `admit`'s grammar has no `frame` property at all, so this rule is
  vacuously true for `admit` by construction.
- **Effect/refuse frame targets must be declared.** Every `effect`/
  `refuse` frame entry (parenthesized selector stripped, e.g.
  `Balance(from)` -> `Balance`) must name a declared node/store/cache/
  queue/cdn/balancer id, else `UnknownReference`.
- **Refuse is audit-only.** Every `refuse` frame target must additionally
  carry the `append_only` marker (a node's `attr append_only;` or a
  store's `append_only` property), else `FrameViolation` -- the refusal
  frame may only ever grow an audit log, never mutate real state.
- **Record audit target must exist.** `record { audit to X }` with an
  undeclared `X` is `UnknownReference`; when it exists, elaboration emits
  one unconditioned `Flow` (`<boundary>__audit`, label `Internal`) from
  the boundary's underlying flow `dst` to `X`.
- **Error-response labeling.** `refuse { respond L }`'s `L` must be a
  level in the kernel `LABELS` lattice (`_models.py::LABELS`), else
  `UnknownLevel` -- an error response naming an undeclared label cannot be
  checked for a leak.
- **Effect frames are outcome-conditioned writes.** Every `effect` frame
  target becomes one `Flow` (`<boundary>__effect_<target>`) from the
  boundary's underlying flow `dst` to the target, conditioned
  `FlowCondition(outcome=Outcome.OK)` -- the kernel's one graph extension
  (docs/strata/kernel.md#data-models), reused rather than duplicated.
- **Operation `on`/`atomic via` must be declared,** else
  `UnknownReference`. Every `modifies { ... } on Ok|Err` frame target
  becomes one `Flow` (`<op>__ok_<i>`/`<op>__err_<i>`) from `on` to the
  target, conditioned on the matching `Outcome`; unlike boundary effect
  frames, operation frame targets are NOT required to be declared node
  ids in v0 -- `docs/strata/boundary.md`'s own `Balance(from)` example
  names a sub-entity of the store, not a separate node, and forcing one
  would misrepresent the source language.
- **Cross-store refusal (the strong guarantee).** When `modifies {} on
  Err` is declared (the empty-err-frame claim) and `atomic via` names
  neither the operation's own `on` store nor a node carrying the
  `coordinator` attr, elaboration fails `CrossStoreAtomicity` --
  "distributed atomicity by wishful thinking is a 'not possible'
  diagnostic, never a silent acceptance" (see "Cross-store refusal"
  above). A nonempty `modifies { ... } on Err` frame is always legal
  regardless of `atomic via`, since the strong guarantee is specifically
  the *empty*-err-frame claim.
- **Panics supervisor must be declared,** else `UnknownReference`; the
  marker becomes a `panics=<supervisor-id>` node attr.
- **Observe target must be declared** (`UnknownReference`) **and every log
  class must be one of** `{error_paths, state_transitions,
  boundary_crossings, crash_events}` (`UnknownLogClass` otherwise --
  chosen as an elaboration error, not a parse error, since the fixed
  vocabulary is a semantic fact the grammar need not hard-code). A
  satisfied `observe` block generates one `Flow` (`<node>__obs`, label
  `Internal`) from the node to its `to` target.
- **`errors_total` without `observe` is a non-fatal diagnostic,** logged
  at WARNING ("errors_total without observe") rather than failing --
  wiring this into a `frob check` gate (ERR/OBS) is phase 4 (T-0070
  scope note), so v0 cannot yet treat it as a hard requirement without a
  gate to explain why.

### Deviation: `modifies` frame targets skip existence checking

Unlike boundary `effect`/`refuse` frames (which name real declared nodes
and therefore can and must resolve), `operation`'s `modifies` frame
targets are treated as opaque strings for flow construction -- this means
the generated `<op>__ok_*`/`<op>__err_*` flows can have a `dst` that is
not a declared node, which `_facts.py::build_facts` will legitimately
reject with `UnknownReference` if nothing else declares that id. This is
intentional and documented, not an oversight: it is the caller's job (an
end-to-end module, not the elaborator) to also declare a node/store
matching each entity a `modifies` frame names, exactly as
`tests/unit/strata/test_observe.py::TestEndToEnd` does.

### Review note: omission equals the strong guarantee

An `operation` with NO `on Err` clause is checked exactly as if
`modifies {} on Err` were declared: omission defaults to the strong
guarantee, and the cross-store atomicity refusal applies to it
identically. Stricter than lax, fails closed (T-0069 review finding).
