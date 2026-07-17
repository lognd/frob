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
