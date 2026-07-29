# strata reliability family: REL2xx (T-0640, T-0644, T-0641, T-0642, T-0643, T-0645)

Home for the T-0331 systems-checks epic's reliability catalog line "TIMEOUT
on every remote/cross-boundary flow" -- the first REL2xx family to land.
Mirrors `docs/strata/host.md#resource-contention-sys2xx-t-0699`'s shape
deliberately: a rule module (`_reliability.py`), a `Report`/`Violation`
pydantic pair, the SAME T-0174 waiver channel, and `frob sys audit` CLI
wiring.

## REL2xx: TIMEOUT obligation (T-0640)

<!-- frob:invariant INV-047 -->

`_reliability.py::check_reliability_timeouts` reads `KernelModel.flows`
(no new kernel field, charter law 1) to find two kinds of unbounded-hang
risk:

- **REL200 missing timeout** -- a flow with no `timeout` attr and no
  `async`/`local` exemption. Every `Flow` in this grammar already crosses
  a real process/service boundary by construction (`_models.py::Flow`'s
  docstring: "directed movement of anything between two nodes" -- there
  is no in-process/self-flow construct), so deny-by-default applies to
  the WHOLE flow set unless a modeler explicitly exempts a flow.
- **REL201 unproven timeout** -- a flow DOES declare `timeout`, but the
  T-0331 PROVABILITY CONSTRAINT forbids discharging an obligation by bare
  declaration alone: the flow's ORIGINATING node (`flow.src`, the caller
  that would hold a bounded-wait argument at the real call site) must
  have at least one file bound to it (`_code_binding.py::bind_code`)
  containing a real `timeout=`-shaped token. A node with no bound code at
  all is UNCHECKABLE, not unproven -- silent rather than a guessed-at
  proof (the same ceiling `_contention.py`'s SYS203 `store_ids` and
  `_selfconform.py`'s `managed` exemption already establish).

### Surface vocabulary

Three Flow `attr` markers, all bare (no `=value`):

```
flow f1 : caller -> worker {
    attr timeout;   // discharges REL200; REL201 then checks caller's bound code
}

flow f2 : caller -> queue {
    attr async;     // fire-and-forget, exempt from REL200 entirely
}

flow f3 : a -> b {
    attr local;     // explicitly modeled as not crossing a real boundary
}
```

### GRAMMAR-DATA CEILING, HONESTLY

`timeout` is presence-only, no magnitude. `strata-core/src/parse/grammar_core.rs`'s
generic `attr KEY=VALUE` clause only lexes an identifier VALUE (letters/
`_`/digits, but never digit-led), so a real duration literal like `30s`
cannot round-trip through today's surface grammar without a dedicated
parser clause -- a `strata-core` change, out of scope for this ticket
(`src/frob/strata/**`/`docs/strata/**`/`tests/unit/strata/**` only).
REL200/REL201 therefore prove PRESENCE of a caller-declared timeout
obligation and its code-level evidence, not a specific bound duration.

`_crash.py`'s existing `Flow.timeout: Quantity | None` typed field
(magnitude-aware, feeding the no-hang check joined to `on crash`
contracts, T-0074) is a SEPARATE, narrower mechanism this family does not
duplicate or replace -- that field is populated only by direct Python
construction today (no grammar clause sets it either), scoped to
synchronous flows into crashable nodes specifically. A future grammar
ticket adding a real `timeout <quantity>` flow clause could unify the
two typed/attr representations; T-0640 does not attempt that unification.

REL201's proof-against-code is a syntactic token scan (`\btimeout\s*=`
over the caller's bound Python source), not a semantic call-argument
binding -- it proves the caller's bound code contains real evidence of a
timeout-shaped construct, not that the SAME call the flow models is the
one carrying it. The honest "ship what current tooling supports" line
`_contention.py`'s MODE-BLIND framing already established for SYS203.

### Waiver channel

REL200/REL201 join the SAME T-0174 waiver channel SYS100-102/SYS200-203
use (`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`) -- a node can originate
more than one flow, so a `waive` clause naming REL200/REL201 MUST carry a
`RULE:SUBTARGET` sub-target (the flow id):

```
node caller : trusted {
    waive "REL200:f1" reason "f1 is a dev-only debug hook, tracked in T-0640" ticket "T-0640";
}
```

## REL21x: HEALTH obligation (T-0644)

`_reliability.py::check_reliability_health` reads `KernelModel.nodes`
(no new kernel field, charter law 1) to find every long-lived service/
daemon node -- one that carries the T-0261 std.host `unit` (systemd) or
`service` (Windows SCM) attr -- with an undischarged (or unproven)
health/liveness/readiness obligation:

- **REL210 missing health surface** -- a `unit`/`service` node with no
  `health` attr and no exemption. Deny-by-default, node-scoped analog of
  REL200.
- **REL211 unproven health surface** -- a node DOES declare `health`, but
  the T-0331 PROVABILITY CONSTRAINT forbids discharging it by bare
  declaration alone: the node must have at least one file bound to it
  (`_code_binding.py::bind_code`) containing a real health/liveness/
  readiness-probe-shaped token. A node with no bound code at all is
  UNCHECKABLE, not unproven -- the same ceiling REL201 draws.

### Surface vocabulary

One Node `attr` marker, bare (no `=value`):

```
node api : trusted {
    unit;           // T-0261 std.host: long-lived systemd daemon
    health;         // discharges REL210; REL211 then checks api's bound code
}

node batch_job : trusted {
    unit;           // long-lived daemon, but declares no health surface
    // REL210 fires here
}
```

### GRAMMAR-DATA CEILING, HONESTLY

Unlike `timeout`, `health` needs no magnitude -- it is a bare presence
marker exactly like `async`/`local`, so (unlike T-0640) NO strata-core
grammar change is even relevant here: there is no digit-led-literal
ceiling to disclose for this family. REL211's proof-against-code is a
syntactic token scan (a `/health`-style route, a k8s-manifest-style
`livenessProbe`/`readinessProbe` key, or a `health_check`/`healthz`
identifier) over the node's bound source, not a semantic route-binding --
the same "ship what current tooling supports" honesty line REL201 draws
for `timeout=`.

### Waiver channel

REL210/REL211 do NOT join `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`,
unlike REL200/REL201: a node carries at most one `unit`/`service` marker
and can fire at most one REL210 and one REL211 finding, so a bare-rule
`waive` clause names exactly one thing (the same carve-out LINT/PII/
COMPLIANCE already use):

```
node legacy_daemon : trusted {
    unit;
    waive "REL210" reason "legacy service, health endpoint tracked in T-0644-followup" ticket "T-0644";
}
```

## REL22x: RETRY obligation (T-0641)

`_retry.py::check_retry_obligations` reads `KernelModel.flows` (no new
kernel field, charter law 1) to find every flow marked `retry` (a hop
retried on failure) with an undischarged backoff/jitter obligation, an
unguarded non-idempotent retry target, or unproven backoff:

- **REL220 missing backoff/jitter** -- a `retry` flow with no
  `backoff_jitter` attr. Deny-by-default: a naive retry with no
  backoff/jitter is a retry-storm risk.
- **REL221 non-idempotent retry with no idempotency key** -- a `retry`
  flow whose DESTINATION node is neither `idempotent`
  (`_models.py`'s existing at-least-once-delivery marker, reused) nor
  `idempotency_key` (a caller-attached dedup key that makes an otherwise
  non-idempotent mutating op safe under retry). Deny-by-default: retrying
  a non-idempotent op with neither marker risks a duplicate side-effect
  on every retry.
- **REL222 unproven backoff** -- a flow DOES declare `backoff_jitter`,
  but the T-0331 PROVABILITY CONSTRAINT forbids discharging it by bare
  declaration alone: at least one of the flow's endpoints (`src` or
  `dst`, T-0758 proof-anchoring) must have bound code
  (`_code_binding.py::bind_code`) containing a real backoff/jitter-shaped
  token. A flow with NEITHER endpoint bound to any code at all is
  UNCHECKABLE, not unproven -- the same ceiling REL201 draws.

### Surface vocabulary

Three markers, all bare (no `=value`) -- two on the Flow, one on the Node:

```
flow f1 : caller -> worker {
    attr retry;           // this hop is retried on failure
    attr backoff_jitter;  // discharges REL220; REL222 then checks bound code
}

node worker : trusted {
    idempotency_key;       // discharges REL221 for retries targeting worker
}
```

### GRAMMAR-DATA CEILING, HONESTLY

Like `timeout`, `retry`/`backoff_jitter` are presence-only bare Flow
attrs (no numeric magnitude -- the same digit-led-literal ceiling
`strata-core/src/parse/grammar_core.rs`'s generic `attr KEY=VALUE` clause imposes on
`timeout`), so REL220/REL222 prove PRESENCE of a caller-declared
backoff/jitter obligation and its code-level evidence, not a specific
bound count/multiplier. `idempotency_key` is likewise a bare NODE marker
(presence-only, no actual key name round-trips through the grammar) --
same ceiling, no `strata-core` change needed (this ticket's scope is
`src/frob/strata/**`/`docs/strata/**`/`tests/unit/strata/**` only, same
as T-0640's).

REL222's proof-against-code is a syntactic token scan (`backoff=`/
`jitter=` kwargs, `exponential_backoff(`, a `@retry(`/`tenacity` call)
over the bound endpoint's source, not a semantic call-argument binding --
the same "ship what current tooling supports" honesty line REL201
establishes for `timeout=`.

### Shared proof-against-code plumbing (T-0641)

`_obligation_proof.py` is the ONE home for the owner-index/bound-code/
token-scan trio every REL2xx proof-against-code rule needs
(`owner_index`, `node_has_bound_code`, `files_evidence_token`,
`bound_endpoints`) -- promoted out of `_reliability.py`'s own private
copies (T-0640) so REL22x/REL23x/REL24x share one implementation rather
than re-deriving the identical pattern per obligation (charter: no
duplication). `_reliability.py` itself keeps its own original copies
unchanged (already shipped; re-deriving its internals mid-family was out
of scope for T-0641) -- new REL2xx modules import from
`_obligation_proof.py` instead.

### Waiver channel

REL220/REL221/REL222 join the SAME T-0174 waiver channel REL200/REL201
use (`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`) -- a node can originate
more than one retryable flow, so a `waive` clause naming one of these
MUST carry a `RULE:SUBTARGET` sub-target (the flow id):

```
node caller : trusted {
    waive "REL220:f1" reason "f1 is a dev-only debug hook, tracked in T-9901" ticket "T-9901";
}
```

## REL23x: CIRCUIT BREAKER / bulkhead obligation (T-0642)

`_circuit_breaker.py::check_circuit_breaker_obligations` reads
`KernelModel.nodes` (no new kernel field, charter law 1) to find every
node marked `external` (a real external dependency -- a third-party
service, a foreign registry, anything outside this system's own blast
radius) with an undischarged or unproven circuit-breaker/bulkhead
obligation. Extends `_lint.py`'s LINT004 kill-switch idea (a risky
capability needs an operator escape hatch) to a new population: a node
that DEPENDS on something external needs its own escape hatch against
that dependency's failure.

- **REL230 missing circuit breaker/bulkhead** -- an `external` node with
  no `circuit_breaker` attr and no exemption. Deny-by-default, node-scoped
  analog of REL200/REL220.
- **REL231 unproven circuit breaker** -- a node DOES declare
  `circuit_breaker`, but the T-0331 PROVABILITY CONSTRAINT forbids
  discharging it by bare declaration alone: the node must have at least
  one file bound to it (`_code_binding.py::bind_code`) containing a real
  circuit-breaker/bulkhead-shaped token. A node with no bound code at all
  is UNCHECKABLE, not unproven -- the same ceiling REL201/REL211/REL222
  draw.

### Surface vocabulary

Three Node `attr` markers, all bare (no `=value`):

```
node payments_api : untrusted {
    external;         // this node models a real external dependency
    critical;         // shared with REL24x FALLBACK (T-0643): this
                       // dependency's failure is not tolerable unguarded
    circuit_breaker;   // discharges REL230; REL231 then checks bound code
}
```

`critical` is defined in `_circuit_breaker.py` (not `_fallback.py`)
specifically so T-0643's FALLBACK obligation can import and reuse the
SAME dependency-criticality classification rather than re-deriving it --
the reason T-0643 is `blocked_by` this ticket.

### GRAMMAR-DATA CEILING, HONESTLY

`external`/`circuit_breaker`/`critical` are all presence-only bare Node
attrs (no numeric magnitude -- the same digit-led-literal ceiling every
other REL2xx marker in this family discloses), so REL230/REL231 prove
PRESENCE of a declared circuit-breaker/bulkhead obligation and its
code-level evidence, not a specific failure threshold or half-open
timing. REL231's proof-against-code is a syntactic token scan
(`circuit_breaker`/`circuitbreaker`/`pybreaker`/`CircuitBreaker(`/
`bulkhead`/`Bulkhead(`) over the node's bound source, not a semantic
call-argument binding -- the same "ship what current tooling supports"
honesty line REL201/REL211/REL222 already establish.

### Waiver channel

REL230/REL231 do NOT join `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`,
same as REL210/REL211: a node carries at most one `external` marker and
fires at most one REL230 and one REL231 finding, so a bare-rule `waive`
clause names exactly one thing:

```
node legacy_gateway : untrusted {
    external;
    waive "REL230" reason "legacy gateway, circuit breaker tracked in T-9902-followup" ticket "T-9902";
}
```

## REL24x: FALLBACK/graceful-degradation obligation (T-0643)

`_fallback.py::check_fallback_obligations` reads `KernelModel.nodes` (no
new kernel field, charter law 1) to find every node marked `critical`
(reusing `_circuit_breaker.py::is_critical_dependency` -- the same
dependency-criticality classification T-0642 already defines, the reason
this ticket is `blocked_by` that one) with an undischarged or unproven
fallback/graceful-degradation obligation.

- **REL240 missing fallback** -- a `critical` node with no `fallback`
  attr and no exemption. Deny-by-default: an unguarded call into a
  CRITICAL dependency with no degraded-mode path risks a full outage the
  moment that dependency fails, not just a slow/expensive call.
- **REL241 unproven fallback** -- a node DOES declare `fallback`, but the
  T-0331 PROVABILITY CONSTRAINT forbids discharging it by bare
  declaration alone: the node must have at least one file bound to it
  (`_code_binding.py::bind_code`) containing a real fallback/graceful-
  degradation-shaped token. A node with no bound code at all is
  UNCHECKABLE, not unproven -- the same ceiling REL201/REL211/REL222/
  REL231 draw.

### Surface vocabulary

One Node `attr` marker, bare (no `=value`), layered on top of REL23x's
`critical` marker:

```
node payments_api : untrusted {
    external;
    critical;          // REL23x/REL24x shared dependency-criticality marker
    circuit_breaker;
    fallback;          // discharges REL240; REL241 then checks bound code
}
```

### GRAMMAR-DATA CEILING, HONESTLY

`fallback` is a presence-only bare Node attr (no numeric magnitude -- the
same digit-led-literal ceiling every other REL2xx marker in this family
discloses), so REL240/REL241 prove PRESENCE of a declared fallback
obligation and its code-level evidence, not a specific degraded-mode
behavior. REL241's proof-against-code is a syntactic token scan
(`fallback`/`graceful_degrad`/`degraded`/`degrade(`/`cached_default`/
`stale_cache`/`stale_value`/`stale_read`) over the node's bound source,
not a semantic call-argument binding -- the same "ship what current
tooling supports" honesty line REL201/REL211/REL222/REL231 already
establish.

### Waiver channel

REL240/REL241 do NOT join `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`,
same as REL210/REL211/REL230/REL231: a node carries at most one
`critical` marker and fires at most one REL240 and one REL241 finding, so
a bare-rule `waive` clause names exactly one thing:

```
node legacy_gateway : untrusted {
    critical;
    waive "REL240" reason "legacy gateway, fallback path tracked in T-9904-followup" ticket "T-9904";
}
```

## REL25x: SPOF detection (T-0645)

`_spof.py::check_spof` reads `KernelModel.nodes`/`KernelModel.flows` (no
new kernel field, charter law 1) to find every node receiving at least
one `critical` inbound flow whose own declared `Capacity` is a
structural singleton -- unlike every sibling REL2xx family in this
ticket cluster, REL25x is ONE rule, not a missing/unproven pair: SPOF is
a structural fact readable straight off the model, not an operator-
declared obligation needing separate proof-against-code.

- **REL250 SPOF** -- a node that is the `dst` of at least one `critical`
  flow, AND whose capacity is a structural singleton
  (`node.capacity is None`, defaulting to `_models.py::Capacity`'s own
  `replicas_max=1`, or a declared `Capacity` with `replicas_max == 1`
  per `Capacity.singleton`), AND does not carry the `redundant`
  exemption attr. Deny-by-default with a reasoned waive channel
  (T-0174), same discipline every REL2xx obligation in this cluster
  uses.

### Surface vocabulary

```
flow f_checkout : web -> inventory {
    attr critical;      // this inbound path must not be lost
}

node inventory : trusted {
    // no `capacity` declared at all -- defaults to replicas_max=1
    // REL250 fires here
}

node inventory_ha : trusted {
    redundant;           // explicit modeler assertion: real redundancy
                          // exists outside what Capacity expresses
}
```

`critical` here is a FLOW attr (`_models.py::Flow.attrs`), reusing the
exact string T-0642's `CRITICAL_ATTR` uses on `Node.attrs` -- deliberately
the same word at two independent grammar sites (a node can be a critical
DEPENDENCY of its caller, T-0642/T-0643's sense; a flow can be a critical
INBOUND PATH into its destination, this rule's sense), not imported from
`_circuit_breaker.py` since the two are independent declarations.

### GRAMMAR-DATA CEILING, HONESTLY

`critical` (on a Flow) and `redundant` (on a Node) are bare presence-only
attrs -- the same ceiling every other REL2xx marker in this family
discloses. `replicas_max` needs no ceiling disclosure at all:
`Capacity.replicas_max` is already a typed `int` field on the EXISTING
`Capacity` model, not a bare attr -- REL250 is the one rule in this
ticket cluster with no proof-against-code companion, because there is
nothing beyond the declared capacity itself to prove.

### Waiver channel

REL250 does NOT join `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`, same
as REL210/REL211/REL230/REL231/REL240/REL241: a node fires at most one
REL250 finding, so a bare-rule `waive` clause names exactly one thing:

```
node legacy_singleton : trusted {
    waive "REL250" reason "legacy singleton, HA migration tracked in T-9903-followup" ticket "T-9903";
}
```

## REL26x: BACKPRESSURE obligation (T-0646)

`_backpressure.py::check_backpressure_obligations` reads
`KernelModel.nodes` (no new kernel field, charter law 1) to find every
node marked `queue` or `consumer` (this node buffers or drains work -- a
message queue, a worker pool consumer, anything that can receive faster
than it can drain) with an undischarged or unproven bounded-intake
obligation. Extends `_lint.py`'s LINT003 surge/LINT005 capacity ideas to
a NEW population: a queue/consumer needs its OWN declared bounded-intake
policy, not just a downstream capacity headroom claim.

- **REL260 missing bounded intake** -- a `queue`/`consumer` node with no
  `bounded_intake` attr. Deny-by-default: an unbounded queue accepts
  intake without limit, so a slow/failed consumer becomes an unbounded
  memory/latency liability.
- **REL261 unproven bounded intake** -- a node DOES declare
  `bounded_intake`, but the T-0331 PROVABILITY CONSTRAINT forbids
  discharging it by bare declaration alone: the node must have at least
  one file bound to it (`_code_binding.py::bind_code`) containing a real
  bounded-queue/backpressure-shaped token. A node with no bound code at
  all is UNCHECKABLE, not unproven -- the same ceiling REL201/REL222/
  REL231 draw.

### Surface vocabulary

```
node ingest_queue : trusted {
    queue;            // this node models a message/work queue
    bounded_intake;    // discharges REL260; REL261 then checks bound code
}

node worker_pool : trusted {
    consumer;
    bounded_intake;
}
```

### GRAMMAR-DATA CEILING, HONESTLY

`queue`/`consumer`/`bounded_intake` are all presence-only bare Node attrs
(no numeric magnitude -- the same digit-led-literal ceiling every other
REL2xx marker in this family discloses), so REL260/REL261 prove PRESENCE
of a declared bounded-intake obligation and its code-level evidence, not
a specific queue depth or drop policy. REL261's proof-against-code is a
syntactic token scan (`maxsize=`/`max_size=` kwarg, `Semaphore(`/
`BoundedSemaphore(`, `backpressure`/`bounded_queue`/`token_bucket`/
`rate_limit`) over the node's bound source, not a semantic call-argument
binding -- the same "ship what current tooling supports" honesty line
REL201/REL222/REL231 already establish.

### Waiver channel

REL260/REL261 do NOT join `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`,
same as REL210/REL211/REL230/REL231/REL240/REL241/REL250: a node carries
at most one `queue`/`consumer` marker and fires at most one REL260 and
one REL261 finding, so a bare-rule `waive` clause names exactly one
thing:

```
node legacy_queue : trusted {
    queue;
    waive "REL260" reason "legacy queue, bounded intake tracked in T-9910-followup" ticket "T-9910";
}
```

## REL27x: OBSERVABILITY + CORRELATION obligation (T-0647)

`_observability.py::check_observability_obligations` reads
`KernelModel.flows`/`KernelModel.boundaries` (no new kernel field,
charter law 1) to find every boundary flow with an undischarged or
unproven observability obligation, and every chained (non-first-hop)
flow with no trace-id correlation propagation.

- **REL270 missing observability** -- a flow attached to a `Boundary`
  with no `observability` attr. Deny-by-default: a boundary crossing
  with no metrics/traces/logs instrumentation is an unobserved trust/
  label change.
- **REL271 unproven observability** -- a boundary flow DOES declare
  `observability`, but the T-0331 PROVABILITY CONSTRAINT forbids
  discharging it by bare declaration alone: at least one of the flow's
  endpoints (`src` or `dst`, T-0758 proof-anchoring) must have bound code
  containing a real metrics/tracing/logging-shaped token. A flow with
  NEITHER endpoint bound to any code at all is UNCHECKABLE, not unproven
  -- the same ceiling REL201/REL222/REL231/REL261 draw.
- **REL272 missing correlation propagation** -- a flow that is NOT the
  first hop of its chain (some other flow's `dst` equals this flow's
  `src`) with no `correlation` attr. Deny-by-default: a chained call with
  no propagated trace-id breaks distributed tracing at exactly the hop
  boundary that matters most for cross-service debugging.

### Surface vocabulary

Two independent Flow `attr` markers, both bare (no `=value`):

```
flow f_edge : edge -> api {
    attr observability;  // discharges REL270; REL271 then checks bound code
}

boundary b_edge on f_edge : endorse foreign -> authenticated;

flow f_chain : api -> db {
    attr correlation;    // discharges REL272 (only applies to chained hops)
}
```

`observability` and `correlation` are deliberately separate markers (not
one combined attr): a single-hop boundary flow can need observability
without ever being part of a chain, and an internal chained hop can need
correlation propagation without crossing any trust/label boundary.

### GRAMMAR-DATA CEILING, HONESTLY

`observability`/`correlation` are both presence-only bare Flow attrs (no
numeric magnitude, no actual trace-id format round-trips through the
grammar -- the same digit-led-literal ceiling every other REL2xx marker
in this family discloses), so REL270/REL271/REL272 prove PRESENCE of a
declared instrumentation/propagation obligation and its code-level
evidence (REL271 only), not a specific metric name or trace header
format. REL271's proof-against-code is a syntactic token scan
(`prometheus`/`statsd`, `opentelemetry`/`otel`, `tracer.start`/
`start_as_current_span`, `logger.`/`logging.`) over the bound endpoint's
source, not a semantic call-argument binding -- the same "ship what
current tooling supports" honesty line REL201/REL222/REL231/REL261
already establish.

### Waiver channel

REL270/REL271/REL272 join the SAME T-0174 waiver channel REL200/REL201/
REL220/REL221/REL222 use (`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`) --
a node can originate more than one boundary or chained flow, so a `waive`
clause naming one of these MUST carry a `RULE:SUBTARGET` sub-target (the
flow id):

```
node edge : trusted {
    waive "REL270:f_edge" reason "f_edge is a dev-only debug hook, tracked in T-9911" ticket "T-9911";
}
```

## REL28x: golden-signal SLO + error-budget obligation (T-0648)

`_slo.py::check_slo_obligations` reads `KernelModel.nodes` (no new kernel
field, charter law 1) to find every long-lived service/daemon node
(`_UNIT_ATTR`/`_SERVICE_ATTR`, the IDENTICAL population REL210/REL211
HEALTH already apply to) with an undischarged or unproven golden-signal-
SLO-and-error-budget obligation.

- **REL280 missing golden-signal SLO + error budget** -- a service node
  missing `slo`, `error_budget`, or both. Deny-by-default: a service with
  no declared golden-signal SLOs (latency/traffic/errors/saturation) and
  error budget has no tracked reliability target, so a degradation has
  nothing to breach and nothing pages on.
- **REL281 unproven SLO** -- a node DOES declare both `slo` and
  `error_budget`, but the T-0331 PROVABILITY CONSTRAINT forbids
  discharging it by bare declaration alone: the node must have at least
  one file bound to it containing a real SLO/error-budget-shaped token. A
  node with no bound code at all is UNCHECKABLE, not unproven -- the same
  ceiling REL201/REL222/REL231/REL261/REL271 draw.

This obligation is `blocked_by` T-0647 (OBSERVABILITY) at the ticket
level (an SLO without the underlying signal is unverifiable), but does
NOT hard-wire a runtime check against T-0647's `observability` marker:
`KernelModel` has no node-level "this node's flows are instrumented"
projection today, and adding one would be a kernel-shape change outside
this ticket's rule-module scope. REL280/REL281 read `slo`/`error_budget`
exactly as declared, honoring the dependency at obligation-ordering level
(T-0647 landed first, in the same ticket batch) rather than a code-level
cross-check.

### Surface vocabulary

Two Node `attr` markers, both bare (no `=value`), layered on top of
REL21x's `service`/`unit` marker:

```
node checkout_svc : trusted {
    service;
    slo;            // discharges half of REL280
    error_budget;   // discharges the other half; REL281 then checks bound code
}
```

### GRAMMAR-DATA CEILING, HONESTLY

`slo`/`error_budget` are both presence-only bare Node attrs (no numeric
magnitude -- the same digit-led-literal ceiling every other REL2xx
marker in this family discloses), so REL280/REL281 prove PRESENCE of a
declared golden-signal-SLO-and-error-budget obligation and its code-
level evidence, not a specific latency/error-rate target or budget
percentage. REL281's proof-against-code is a syntactic token scan
(`error_budget`/`errorbudget`, `slo`/`sloth`, a `p50`/`p9[0-9]`
latency-percentile token) over the node's bound source, not a semantic
call-argument binding -- the same "ship what current tooling supports"
honesty line REL201/REL222/REL231/REL261/REL271 already establish.

### Waiver channel

REL280/REL281 do NOT join `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`,
same as REL210/REL211/REL230/REL231/REL240/REL241/REL250/REL260/REL261: a
node carries at most one `unit`/`service` marker and fires at most one
REL280 and one REL281 finding, so a bare-rule `waive` clause names
exactly one thing:

```
node legacy_service : trusted {
    service;
    waive "REL280" reason "legacy service, SLO tracked in T-9912-followup" ticket "T-9912";
}
```

## REL29x: SINGLE SOURCE OF TRUTH obligation (T-0649)

`_ssot.py::check_ssot_obligations` reads `KernelModel.flows`/`KernelModel.
nodes` plus a caller-supplied `store_ids` set (no new kernel field,
charter law 1 -- same `store_ids` parameter shape `_contention.py`'s
SYS203 already established) to find every store written by two or more
distinct nodes with an undischarged or unproven single-source-of-truth
obligation. Extends `_contention.py`'s SYS203 shared-store-write
DETECTION with an OBLIGATION: SYS203 alone only reports the fact of
multi-writer contention; REL290/REL291 additionally require the store to
declare who owns write authority or how conflicting writes reconcile.

- **REL290 missing owner/reconciliation** -- a multi-writer store (>=2
  distinct non-store nodes have a `Flow` edge landing on it, SYS203's
  exact mode-blind detection) with no `owner` attr and no
  `reconciliation` attr. Deny-by-default: two or more nodes writing the
  same store with no declared single-owner authority or reconciliation
  strategy is a hard consistency hazard -- concurrent writers can
  silently clobber each other with no defined resolution.
- **REL291 unproven owner** -- a multi-writer store DOES declare `owner`
  or `reconciliation`, but the T-0331 PROVABILITY CONSTRAINT forbids
  discharging it by bare declaration alone: the store node must have at
  least one file bound to it containing a real single-writer/
  reconciliation-shaped token. A store with no bound code at all is
  UNCHECKABLE, not unproven -- the same ceiling REL201/REL222/REL231/
  REL261/REL271/REL281 draw.

### Surface vocabulary

Two Node `attr` markers, either one sufficient to discharge REL290:

```
node orders_db : trusted {
    owner;            // OR reconciliation; discharges REL290
                       // REL291 then checks bound code
}
```

`store_ids` is NOT a `KernelModel` fact (module docstring, SYS203's same
disclosure): callers pass the design file's `Module.stores` ids
explicitly; an empty `store_ids` emits nothing.

### GRAMMAR-DATA CEILING, HONESTLY

`owner`/`reconciliation` are both presence-only bare Node attrs (no
numeric magnitude, no actual owning-node-id or reconciliation-strategy
name round-trips through the grammar -- the same digit-led-literal
ceiling every other REL2xx marker in this family discloses), so REL290/
REL291 prove PRESENCE of a declared single-source-of-truth obligation and
its code-level evidence, not a specific owning node or algorithm.
REL291's proof-against-code is a syntactic token scan (`single_writer`,
`leader_election`/`leader_only`, `distributed_lock`/`DistributedLock(`,
`reconcil`/`CRDT`) over the store's bound source, not a semantic call-
argument binding -- the same "ship what current tooling supports"
honesty line REL201/REL222/REL231/REL261/REL271/REL281 already
establish.

### Waiver channel

REL290/REL291 do NOT join `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`,
same as REL210/REL211/REL230/REL231/REL240/REL241/REL250/REL260/REL261/
REL280/REL281: a store fires at most one REL290 and one REL291 finding,
so a bare-rule `waive` clause names exactly one thing:

```
node legacy_shared_store : trusted {
    waive "REL290" reason "legacy shared store, owner tracked in T-9913-followup" ticket "T-9913";
}
```

## REL30x: TRANSACTIONAL BOUNDARY obligation (T-0650)

`_txn.py::check_txn_boundary_obligations` reads `KernelModel.flows`/
`KernelModel.nodes` plus the SAME caller-supplied `store_ids` set REL29x
uses (no new kernel field, charter law 1) to find every op (non-store
node) writing to two or more distinct stores with an undischarged or
unproven transactional-boundary obligation. REUSES `_ssot.py`'s store-
writer graph, inverted: REL29x groups multi-writer findings by the STORE
written; REL30x groups them by the OP writing, looking for >=2 distinct
stores per op instead of >=2 distinct writers per store.

- **REL300 missing transactional boundary** -- an op writing (mode-blind:
  ANY outbound `Flow` landing on a distinct store id, the same detection
  style SYS203/REL290 already establish) to >=2 distinct stores with no
  `transaction` attr and no `saga` attr. Deny-by-default: an op spanning
  two or more stores with no declared transactional boundary or saga/
  compensation strategy is a hard consistency hazard -- a partial failure
  between the writes can leave the stores permanently inconsistent with
  no defined recovery.
- **REL301 unproven transactional boundary** -- a multi-store-write op
  DOES declare `transaction` or `saga`, but the T-0331 PROVABILITY
  CONSTRAINT forbids discharging it by bare declaration alone: the op
  node must have at least one file bound to it containing a real
  transaction/saga-shaped token. An op with no bound code at all is
  UNCHECKABLE, not unproven -- the same ceiling REL201/REL222/REL231/
  REL261/REL271/REL281/REL291 draw.

### Surface vocabulary

Two Node `attr` markers, either one sufficient to discharge REL300:

```
node svc_orders : trusted {
    transaction;      // OR saga; discharges REL300
                       // REL301 then checks bound code
}
```

`store_ids` is NOT a `KernelModel` fact (module docstring, SYS203/REL29x's
same disclosure): callers pass the design file's `Module.stores` ids
explicitly; an empty `store_ids` emits nothing.

### GRAMMAR-DATA CEILING, HONESTLY

`transaction`/`saga` are both presence-only bare Node attrs (no numeric
magnitude, no actual coordinator name or compensation strategy round-trips
through the grammar -- the same digit-led-literal ceiling every other
REL2xx/REL29x marker in this family discloses), so REL300/REL301 prove
PRESENCE of a declared transactional-boundary obligation and its code-
level evidence, not a specific coordinator or algorithm. REL301's proof-
against-code is a syntactic token scan (`transaction`, `two_phase_commit`/
`2pc`, `saga`/`Saga(`, `compensat`) over the op's bound source, not a
semantic call-argument binding -- the same "ship what current tooling
supports" honesty line REL201/REL222/REL231/REL261/REL271/REL281/REL291
already establish.

OUT OF SCOPE, DELIBERATELY: the cross-SERVICE distributed-transaction
saga/compensation obligation (a transaction spanning multiple SERVICES,
not just multiple stores written by one op) is a separate, later ticket
that builds on this module's multi-write detection.

### Waiver channel

REL300/REL301 do NOT join `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`,
same as REL210/REL211/REL230/REL231/REL240/REL241/REL250/REL260/REL261/
REL280/REL281/REL290/REL291: an op fires at most one REL300 and one
REL301 finding, so a bare-rule `waive` clause names exactly one thing:

```
node legacy_multi_write_op : trusted {
    waive "REL300" reason "legacy multi-write op, txn tracked in T-9914-followup" ticket "T-9914";
}
```

## REL31x: INTERACTIVE-COST-BOUND obligation (T-0919)

`_interactive_cost.py::check_interactive_cost_obligations` reads
`KernelModel.nodes` (no new kernel field, charter law 1) to find every
node marked `interactive` (a human-facing CLI/foreground command or flow)
with an undischarged or unproven bounded-cost obligation. Generalizes the
`frob ticket done-report` two-full-check-spawns incident (T-0919, fixed
directly in `frob.app.ticket_runner` and flagged mechanically at the code
layer by PERF012 -- `docs/modules/perf.md#duplicate-identical-subprocess-spawn-detector-perf012-t-0919`):
a foreground/interactive flow with no declared cost bound can silently
grow (a new internal spawn added later, a doubled call site) past any
reasonable wait, with nothing statically flagging the drift.

- **REL310 missing bounded cost** -- an `interactive` node with no
  `bounded_cost` attr. Deny-by-default: an interactive flow with no
  declared cost bound is a foreground-hang risk exactly like an unbounded
  queue (REL26x) is an OOM risk.
- **REL311 unproven bounded cost** -- a node DOES declare `bounded_cost`,
  but the T-0331 PROVABILITY CONSTRAINT forbids discharging it by bare
  declaration alone: the node must have at least one file bound to it
  (`_code_binding.py::bind_code`) containing a real cost-bounding-shaped
  token (a shared/deduplicated spawn, a cache/memo, an explicit timeout,
  or a stage-scoped/`--only`-style narrowing). A node with no bound code
  at all is UNCHECKABLE, not unproven -- the same ceiling REL201/REL222/
  REL231/REL261/REL301 draw.

### Surface vocabulary

```
node ticket_done_report : trusted {
    interactive;       // this node is a human-facing CLI/foreground flow
    bounded_cost;       // discharges REL310; REL311 then checks bound code
}
```

### GRAMMAR-DATA CEILING, HONESTLY

`interactive`/`bounded_cost` are both presence-only bare Node attrs (no
numeric magnitude -- the same digit-led-literal ceiling every other
REL2xx/REL3xx marker in this family discloses), so REL310/REL311 prove
PRESENCE of a declared cost-bound obligation and its code-level evidence,
not a specific wall-clock budget. REL311's proof-against-code is a
syntactic token scan (`lru_cache`/`memo`/`cache`, `shared_spawn`/`dedup`/
`bounded_cost`, `timeout=`/`--only`/`once`) over the node's bound source,
not a semantic call-argument binding -- the same "ship what current
tooling supports" honesty line REL201/REL222/REL231/REL261/REL301 already
establish.

### Waiver channel

REL310/REL311 do NOT join `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`,
same as REL210/REL211/REL230/REL231/REL240/REL241/REL250/REL260/REL261/
REL280/REL281/REL290/REL291/REL300/REL301: a node carries at most one
`interactive` marker and fires at most one REL310 and one REL311 finding,
so a bare-rule `waive` clause names exactly one thing:

```
node legacy_interactive_flow : trusted {
    interactive;
    waive "REL310" reason "legacy flow, cost bound tracked in T-9910-followup" ticket "T-9910";
}
```

## REL32x: MESSAGE SCHEMA VERSION obligation (T-0651)

`_message_schema.py::check_message_schema_obligations` reads
`KernelModel.nodes` (no new kernel field, charter law 1) to find every
node marked `event` or `queue` (a published event or a message/work
queue -- both populations that carry a message payload across a
producer/consumer boundary) with an undischarged or unproven message-
schema-version obligation. `event` is a NEW node-attr marker this family
introduces; `queue` is reused unchanged from `_backpressure.py`'s REL26x
population -- a queue is simultaneously subject to REL260/REL261's
bounded-intake obligation AND this family's REL320/REL321 schema-version
obligation (the two families are orthogonal, not exclusive).

- **REL320 missing schema version** -- an `event`/`queue` node with no
  `schema_version` attr. Deny-by-default: an event/queue with no
  declared schema version has no backward-compat tracking -- a producer
  can change the message shape with no version boundary for a consumer
  to detect the break against.
- **REL321 unproven schema version** -- a node DOES declare
  `schema_version`, but the T-0331 PROVABILITY CONSTRAINT forbids
  discharging it by bare declaration alone: the node must have at least
  one file bound to it (`_code_binding.py::bind_code`) containing a real
  schema-version-shaped token. A node with no bound code at all is
  UNCHECKABLE, not unproven -- the same ceiling REL201/REL222/REL231/
  REL261/REL301/REL311 draw.

### Surface vocabulary

```
node order_placed : trusted {
    event;              // this node models a published event
    schema_version;      // discharges REL320; REL321 then checks bound code
}

node ingest_queue : trusted {
    queue;
    schema_version;
}
```

### GRAMMAR-DATA CEILING, HONESTLY

`event`/`queue`/`schema_version` are all presence-only bare Node attrs
(no numeric magnitude -- the same digit-led-literal ceiling every other
REL2xx/REL3xx marker in this family discloses), so REL320/REL321 prove
PRESENCE of a declared schema-version obligation and its code-level
evidence, not a specific version number or compatibility policy. REL321's
proof-against-code is a syntactic token scan (`schema_version=`/
`schemaVersion=`, `SCHEMA_VERSION`, `schema_registry`, an avro/protobuf
schema-with-version construct) over the node's bound source, not a
semantic call-argument binding -- the same "ship what current tooling
supports" honesty line REL201/REL222/REL231/REL261/REL301/REL311 already
establish.

### Waiver channel

REL320/REL321 do NOT join `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`,
same as REL210/REL211/REL230/REL231/REL240/REL241/REL250/REL260/REL261/
REL280/REL281/REL290/REL291/REL300/REL301/REL310/REL311: a node carries
at most one `event`/`queue` marker and fires at most one REL320 and one
REL321 finding, so a bare-rule `waive` clause names exactly one thing:

```
node legacy_event : trusted {
    event;
    waive "REL320" reason "legacy event, schema versioning tracked in T-9910-followup" ticket "T-9910";
}
```

## REL33x: DELIVERY-SEMANTICS obligation (T-0652)

`_delivery_semantics.py::check_delivery_semantics_obligations` reads
`KernelModel.nodes` (no new kernel field, charter law 1) to find every
`queue` node (`_backpressure.py`/`_message_schema.py`'s existing
population, module docstring: a THIRD orthogonal obligation on the same
`queue` marker, alongside REL26x's bounded-intake and REL32x's
schema-version) with an undischarged or unproven delivery-semantics
obligation. A queue with no declared delivery semantics leaves a consumer
unable to reason about duplicate/loss risk: a consumer written assuming
exactly_once processing silently double-applies side effects against an
at_least_once queue, with no declared contract to catch the mismatch.

- **REL330 missing/invalid delivery semantics** -- a `queue` node with no
  `delivery=<value>` attr, or one whose value is not one of the fixed two
  (`exactly_once`, `at_least_once`). Deny-by-default, folded into one
  rule (the `_pii.py::check_pii_catalog` precedent that a malformed
  declaration is itself a form of "not declared" -- neither gives a
  consumer a real contract to code against).
- **REL331 unproven delivery semantics** -- a queue node DOES declare a
  valid `delivery=<value>`, but the T-0331 PROVABILITY CONSTRAINT forbids
  discharging it by bare declaration alone: the node must have at least
  one file bound to it containing a real delivery-semantics-shaped
  token. A node with no bound code at all is UNCHECKABLE, not unproven --
  the same ceiling REL201/REL222/REL231/REL261/REL271/REL281/REL291/
  REL301/REL311/REL321 draw.

### Surface vocabulary

```
node ingest_queue : trusted {
    queue;
    attr delivery=exactly_once;   // OR at_least_once; discharges REL330
                                    // REL331 then checks bound code
}
```

`delivery=<value>` is an IDENT-valued attr (the same
`retention=<value><unit>` convention `_compliance.py` establishes), not a
bare presence-only marker -- this family genuinely needs a two-way
distinction. The grammar's generic `attr KEY=IDENT` clause
(`strata-core/src/parse/grammar_core.rs::Parser::parse_attrval`, already exercised by
its own `attr delivery=at_least_once;` parser fixture) forces the
underscore-joined spelling, not the hyphenated prose form.

### GRAMMAR-DATA CEILING, HONESTLY

`delivery=<value>` proves PRESENCE of one of exactly two catalogued
values and its code-level evidence, not a specific broker configuration
or dedup-window size. REL331's proof-against-code is a syntactic token
scan (`idempotenc*`/`dedup*`/`idempotency_key` for exactly_once,
`ack(`/`nack(`/`redeliver*`/`retry` for at_least_once) over the node's
bound source, not a semantic call-argument binding -- the same "ship
what current tooling supports" honesty line REL201/REL222/REL231/REL261/
REL271/REL281/REL291/REL301/REL311/REL321 already establish.

### Waiver channel

REL330/REL331 do NOT join `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`,
same as REL210/REL211/REL230/REL231/REL240/REL241/REL250/REL260/REL261/
REL280/REL281/REL290/REL291/REL300/REL301/REL310/REL311/REL320/REL321: a
node carries at most one `queue` marker and fires at most one REL330 and
one REL331 finding, so a bare-rule `waive` clause names exactly one
thing:

```
node legacy_queue : trusted {
    queue;
    waive "REL330" reason "legacy queue, delivery semantics tracked in T-9910-followup" ticket "T-9910";
}
```

## REL34x: SYNC CALL-CHAIN DEPTH bound (T-0654)

`_sync_depth.py::check_sync_chain_depth` reads `KernelModel.flows` (no
new kernel field, charter law 1) to find every node reached only via a
too-deep chain of synchronous flow hops. Unlike every sibling REL3xx
family in this ticket cluster, REL34x is ONE RULE, not a missing/unproven
pair (the same `_spof.py`/REL25x shape): call-chain depth is a
STRUCTURAL fact computed straight from the model's flows, not an
operator-declared obligation needing separate proof-against-code.

A synchronous call chain that grows too deep is a cascading-latency/
failure risk: each hop adds its own latency to the critical path, and a
failure at the bottom of a deep chain propagates back through every
synchronous caller above it. A flow marked `async` (`_crash.py::
_ASYNC_ATTR`, reused directly -- the same "this hop does not block its
caller" fact, at the same grammar site) breaks the chain: the depth
measured here does not continue past an async hop.

- **REL340 sync call-chain depth exceeded** -- some node is reached only
  via `SYNC_CHAIN_MAX_DEPTH` (default 4) or more consecutive synchronous
  (non-`async`) flow hops, and does not carry the `deep_chain_ok`
  exemption attr. A synchronous CYCLE feeding a node is treated as an
  unbounded chain (`math.inf`, the same cycle-to-inf discipline
  `_facts.py::FactBase.worst_age` already establishes) -- always fires,
  never silently clamped.

### Surface vocabulary

```
node n0 : trusted {}
node n1 : trusted {}
node n2 : trusted {}
node n3 : trusted {}
node n4 : trusted { deep_chain_ok; }   // exempts n4 from REL340

flow f0 : n0 -> n1 {}
flow f1 : n1 -> n2 {}
flow f2 : n2 -> n3 {}
flow f3 : n3 -> n4 { attr async; }      // breaks the chain past n3
```

### GRAMMAR-DATA CEILING, HONESTLY

`deep_chain_ok` is a presence-only bare Node attr (no numeric magnitude --
the same digit-led-literal ceiling every other REL2xx/REL3xx marker in
this family discloses), so a model cannot declare its own depth bound:
`SYNC_CHAIN_MAX_DEPTH` is a fixed Python-side default, not a per-model
override. This module deliberately does NOT reuse `_facts.py::
FactBase.reachable`'s (T-0282) non-transitive-edge machinery directly --
that machinery's terminal-attr sets are shared, `_facts.py`-owned
constants encoding trust-boundary/KRB/utility semantics for every other
closure consumer (PII, compliance, breach, krb-movement); folding
`async` into that shared set would change taint-closure semantics for
every one of those unrelated callers. REL340 instead computes its own,
narrower longest-path-ending-at-node walk directly over `model.flows`,
applying the SAME underlying "a marked edge is terminal" idea T-0282
introduced, without touching the shared primitive. No `strata-core`
change needed (this ticket's scope is `src/frob/strata/**`/`docs/strata/
**`/`tests/unit/strata/**` only, same as T-0640/.../T-0653's).

### Waiver channel

REL340 does NOT join `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`, same
as every other REL2xx/REL3xx rule in this cluster: a node either is or is
not too deep this run, so a bare-rule `waive` clause names exactly one
thing:

```
node n4 : trusted {
    waive "REL340" reason "reviewed, independent slow paths that do not compound" ticket "T-9910";
}
```

## REL35x: DISTRIBUTED-TRANSACTION-ACROSS-SERVICES obligation (T-0655)

`_distributed_txn.py::check_distributed_txn_obligations` reads
`KernelModel.flows`/`KernelModel.nodes` (no new kernel field, charter
law 1) to find every op writing to two or more distinct downstream nodes
with an undischarged or unproven saga/compensation obligation. BUILDS ON
`_txn.py`'s REL30x multi-write detection (T-0650's own scope-cut note
names this exact ticket), EXTENDED ACROSS SERVICE BOUNDARIES: REL2xx's
own module docstring already discloses that every `Flow` in this grammar
crosses a real process/service boundary by construction -- there is no
in-process/self-flow construct -- so every node already IS its own
service boundary. REL30x needed a caller-supplied `store_ids` set only
to answer the NARROWER "writes to >=2 STORES" question; REL35x asks the
BROADER "writes to >=2 SERVICES" question the ticket names, which is a
plain `KernelModel.flows` fact needing no external input.

- **REL350 missing saga/compensation** -- an op writing (mode-blind: ANY
  outbound `Flow`) to >=2 distinct downstream nodes with no `saga` attr.
  Unlike REL300 (which accepts EITHER `transaction` or `saga`), REL350
  accepts `saga` ONLY: a bare `transaction` attr asserts a single
  coordinated commit, not a meaningful claim once the write fans out
  across independent service processes with no shared commit log.
  Deny-by-default: a distributed write with no declared saga/
  compensation strategy can leave services permanently inconsistent
  after a partial failure, with no defined recovery.
- **REL351 unproven saga** -- a multi-service-write op DOES declare
  `saga`, but the T-0331 PROVABILITY CONSTRAINT forbids discharging it
  by bare declaration alone: the op node must have at least one file
  bound to it containing a real saga/compensation-shaped token. An op
  with no bound code at all is UNCHECKABLE, not unproven -- the same
  ceiling REL201/REL222/REL231/REL261/REL271/REL281/REL291/REL301/
  REL311/REL321/REL331 draw.

### Surface vocabulary

```
node checkout : trusted {
    saga;      // REQUIRED here (unlike REL300, `transaction` alone does
                // not discharge REL350); REL351 then checks bound code
}

flow f1 : checkout -> inventory_svc {}
flow f2 : checkout -> billing_svc {}
```

### GRAMMAR-DATA CEILING, HONESTLY

`saga` is a presence-only bare Node attr (no numeric magnitude -- the
same digit-led-literal ceiling every other REL2xx/REL3xx marker in this
family discloses), so REL350/REL351 prove PRESENCE of a declared saga/
compensation obligation and its code-level evidence, not a specific saga
coordinator or compensation algorithm. REL351's proof-against-code is a
syntactic token scan (`saga`/`Saga(`, `compensat`, `two_phase_commit`/
`2pc`) over the op's bound source, not a semantic call-argument binding
-- the same "ship what current tooling supports" honesty line every
sibling REL2xx/REL3xx rule already establishes.

### Waiver channel

REL350/REL351 do NOT join `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`,
same as every other REL2xx/REL3xx rule in this cluster: an op fires at
most one REL350 and one REL351 finding, so a bare-rule `waive` clause
names exactly one thing:

```
node legacy_multi_write_op : trusted {
    waive "REL350" reason "legacy multi-write op, saga tracked in T-9910-followup" ticket "T-9910";
}
```

## REL36x: NO-SHARED-MUTABLE-STATE-ACROSS-SERVICE-BOUNDARIES obligation (T-0656)

`_shared_state.py::check_shared_state` reads `KernelModel.flows` (no new
kernel field, charter law 1) to find every MUTABLE node (one that is the
`dst` of at least one `Flow` at all -- something writes into it) that is
ACCESSED (touched as either `src` or `dst` of a `Flow`, read OR write) by
`Flow`s connecting it to >=2 distinct other nodes. Unlike every sibling
REL3xx family in this ticket cluster, REL36x is ONE RULE, not a missing/
unproven pair -- the same `_spof.py`/REL25x shape: shared mutable state
is a STRUCTURAL fact readable straight off the kernel model.

RELATIONSHIP TO REL29x (SSOT), DISTINGUISHED: `_ssot.py`'s REL290/REL291
already flag a store written by >=2 distinct nodes with no `owner`/
`reconciliation` declared -- but that obligation is DISCHARGEABLE by
naming who owns write authority; two services may still share the SAME
mutable store as long as conflicts are reconciled. REL36x is a STRICTER,
INDEPENDENT principle: services should not share mutable state directly
at all (communicate via APIs/messages instead), regardless of whether
the sharing is reconciled, so `owner`/`reconciliation` do NOT discharge
REL360 -- only a dedicated `shared_state_ok` exemption does. REL36x's
population is also BROADER: it counts every ACCESSOR (read or write),
not just writers -- a read-only consumer of a store two independent
services write into is still coupled to that store's shape and
lifecycle, the same hazard class.

- **REL360 shared mutable state across service boundaries** -- a mutable
  node accessed by >=2 distinct other nodes, with no `shared_state_ok`
  exemption attr. Every `Flow` in this grammar already crosses a real
  process/service boundary by construction (REL2xx's own module
  docstring), so >=2 distinct accessing nodes IS >=2 distinct services.
  Deny-by-default with a reasoned waive channel (T-0174), same
  discipline every REL2xx/REL3xx obligation in this cluster uses.

### Surface vocabulary

```
node svc_a : trusted {}
node svc_b : trusted {}
node shared_db : trusted {
    shared_state_ok;   // exempts shared_db from REL360
}

flow f1 : svc_a -> shared_db {}
flow f2 : svc_b -> shared_db {}
```

### GRAMMAR-DATA CEILING, HONESTLY

`shared_state_ok` is a presence-only bare Node attr -- the same digit-
led-literal ceiling every other REL2xx/REL3xx marker in this family
discloses. No `strata-core` change needed (this ticket's scope is
`src/frob/strata/**`/`docs/strata/**`/`tests/unit/strata/**` only, same
as T-0640/.../T-0655's).

### Waiver channel

REL360 does NOT join `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`, same
as every other REL2xx/REL3xx rule in this cluster: a node either is or
is not shared mutable state this run, so a bare-rule `waive` clause
names exactly one thing:

```
node legacy_shared_db : trusted {
    waive "REL360" reason "legacy shared db, migration tracked in T-9910-followup" ticket "T-9910";
}
```

## REL37x: CLOCK/ORDERING-ASSUMPTIONS obligation (T-0657)

`_clock_ordering.py::check_clock_ordering_obligations` reads
`KernelModel.flows` (no new kernel field, charter law 1) to find every
flow marked `clock_dependent` (this hop's correctness depends on
comparing timestamps/wall-clock ordering across the two endpoints) with
an undischarged or unproven ordering-strategy obligation, mirroring
`_retry.py`'s REL22x flow-scoped structure. Every `Flow` in this grammar
already crosses a real process/service boundary by construction (REL2xx's
own module docstring), so a `clock_dependent` flow is, by definition, a
distributed clock comparison.

- **REL370 missing ordering strategy** -- a `clock_dependent` flow with
  no `ordering_strategy` attr. Deny-by-default: a clock-dependent flow
  with no declared ordering strategy silently trusts wall-clock
  comparison across independent nodes, which drifts (NTP skew, VM
  migration pauses, leap seconds).
- **REL371 unproven ordering strategy** -- a `clock_dependent` flow DOES
  declare `ordering_strategy`, but the T-0331 PROVABILITY CONSTRAINT
  forbids discharging it by bare declaration alone: at least one of the
  flow's endpoints must have bound code containing a real ordering-
  strategy-shaped token. A flow with NEITHER endpoint bound to any code
  at all is UNCHECKABLE, not unproven -- the same ceiling REL201/REL222/
  REL231/REL261/REL271/REL281/REL291/REL301/REL311/REL321/REL331/REL351
  draw.
- **REL372 wall-clock-only discharge** -- a `clock_dependent` flow
  declares `ordering_strategy`, has bound code, and that code DOES carry
  an ordering-shaped token, but the ONLY such token is a bare wall-clock
  read (`time.time()`/`datetime.now()`-shaped, no vector/logical-clock or
  sequence-number construct alongside it). Flagged distinctly from
  REL371's honest "no evidence at all" silence: this is a modeler who
  declared the obligation and then re-implemented the exact hazard it
  exists to catch.

### Surface vocabulary

```
node replica_a : trusted {}
node replica_b : trusted {}

flow f1 : replica_a -> replica_b {
    attr clock_dependent;
    attr ordering_strategy;   // discharges REL370; REL371/REL372 then
                                // check bound code
}
```

### GRAMMAR-DATA CEILING, HONESTLY

`clock_dependent`/`ordering_strategy` are both presence-only bare Flow
attrs (no numeric magnitude, no actual clock algorithm name round-trips
through the grammar -- the same digit-led-literal ceiling every other
REL2xx/REL3xx marker in this family discloses), so REL370/REL371/REL372
prove PRESENCE of a declared ordering obligation and its code-level
evidence, not a specific clock algorithm. REL371/REL372's proof-against-
code is a syntactic token scan (`vector_clock`/`logical_clock`/
`lamport`/`sequence_number`/`happens_before`/`hlc` for a real ordering
construct; `time.time(`/`datetime.now(`/`System.currentTimeMillis` for
the wall-clock-only anti-pattern) over the bound endpoint(s)' source, not
a semantic call-argument binding -- the same "ship what current tooling
supports" honesty line every sibling REL2xx/REL3xx rule already
establishes.

### Waiver channel

REL370/REL371/REL372 DO join `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`
(same as REL200/REL201/REL220/REL221/REL222/REL270/REL271/REL272): a node
can originate several `clock_dependent` flows, so a waive clause must
name the specific flow via the `RULE:FLOW_ID` sub-target convention:

```
node replica_a : trusted {
    waive "REL370:f1" reason "legacy flow, ordering tracked in T-9910-followup" ticket "T-9910";
}
```

## REL38x: STARVATION/THROUGHPUT obligation (T-0703)

`_starvation.py::check_starvation_obligations` reads the T-0700 `access
"R" mode M`/`resource ID { arbitrated_by | lock }` grammar
(`docs/strata/host.md#resource-access-modes-t-0700`) together with the
T-0702 demand-propagation fact `FactBase.aggregate_demand`
(`docs/strata/kernel.md#demand-declarations-t-0702`) to find every
serialization point whose aggregate inbound demand already outruns its
capacity, every read-heavy resource whose write-like accessor can be
perpetually starved, and every contended-resource acquisition with no
declared timeout. The user mandate motivating this family: 500k declared
users flowing into a database node accessed in `mode exclusive` -- a
single-writer serialization point overwhelmed by orders of magnitude,
which no purely structural check (SPOF, contention) can see without the
demand arithmetic this family adds.

THREE obligations, each its own rule id (not a missing/unproven pair --
module docstring: REL380/REL381 read real typed model data, `Capacity.
service_rate` and `FactBase.aggregate_demand`, the same `_spof.py`/
`_shared_state.py` "structural fact, no proof-against-code needed" shape):

- **REL380 serialization-point utilization over threshold** -- a node
  that is an effective-concurrency-1 point for some resource (it
  declares `access "R" mode M` with M one of `write`/`append`/
  `exclusive`/`alpha`, OR it is the resource's own declared
  `arbitrated_by` node) whose aggregate inbound demand
  (`FactBase.aggregate_demand`) exceeds its capacity
  (`Capacity.service_rate`, ONE replica's worth -- deliberately NOT
  multiplied by `replicas_max`, since exclusivity collapses effective
  concurrency to 1 regardless of replica count). A node with no declared
  `Capacity` falls back to a conservative default holding time (10ms,
  i.e. a default capacity of 100/s) rather than being treated as
  infinite capacity. The finding SHOWS THE ARITHMETIC: demand, capacity,
  and the resulting utilization multiple, never a bare "too much load"
  claim.
- **REL381 serialization-point demand undeclared** -- the SAME
  population as REL380, but firing instead of REL380 whenever no
  `users`/`rate` declaration's demand reaches the node at all
  (`AggregateDemand.declared is False`) -- fail-closed: an exclusive/
  arbitrated serialization point with unknown upstream demand is never
  silently skipped just because the arithmetic cannot be filled in.
- **REL382 writer starvation (advisory)** -- a resource with at least
  one `read` accessor and at least one write-like accessor
  (`write`/`append`/`exclusive`), but NO `alpha` accessor declared for
  it. T-0700's own `alpha` semantics ("sits between read and write ...
  alpha never conflicts with readers") exist precisely so a writer can
  register upgrade-intent without blocking readers outright; a resource
  with readers and a writer but no alpha discipline lets readers
  perpetually preempt the writer. Fires regardless of utilization (even
  a lightly-loaded resource can starve a writer under a read-preferring
  lock) and regardless of whether an arbiter is declared (an arbiter
  changes who waits, not whether the discipline can starve a writer).
- **REL383 unbounded wait** -- a node acquiring a CONTENDED resource
  (2+ total accessors declared for the same resource id) in a
  write-like/alpha mode, with no `timeout` attr declared on the
  acquiring node itself. Reuses the T-0640 TIMEOUT family's own
  vocabulary (`_reliability.py`'s `timeout` attr string) at this
  module's own population (a contended-resource accessor, not a `Flow`)
  -- "joins the T-0640 timeout obligation family" in spirit, without
  touching `_reliability.py` itself (one rule module per obligation,
  same discipline T-0700 established adding SYS204 alongside SYS200-203
  rather than editing `_contention.py`).

COORDINATION WITH T-0645/T-0646, DISCLOSED: REL380 (a saturated single
arbiter) is the QUANTITATIVE version of T-0645's REL250 SPOF (a
structural singleton receiving a critical inbound flow) -- deliberately
NOT merged, since they read different declarations (`critical` Flow attr
vs `access`/`resource`) and can fire independently of each other. T-0646
REL260/REL261 ask "is intake at this queue/consumer bounded at all";
REL380 asks "does the number already exceed capacity" -- a node can be
REL260-clean and REL380-dirty at the same time (a declared bound too
small for the demand reaching it), so both obligations coexist without
collapsing into one.

### Surface vocabulary

```
node entry : trusted { users 500000; }
node db : trusted {
    access "ledger" mode exclusive;
    // no capacity declared -> default 10ms holding time -> REL380 fires,
    // demand=500000/s vastly exceeds the 100/s default capacity
}

flow f1 : entry -> db { }

resource cache_res {
    arbitrated_by cache_arbiter;
}
node cache_arbiter : trusted {
    capacity { service_rate 10000 per_second; }
}
node reader_a : trusted { access "cache_res" mode read; }
node reader_b : trusted { access "cache_res" mode read; }
node writer : trusted {
    access "cache_res" mode write;
    // >=1 reader, a writer, no alpha accessor anywhere -> REL382 advisory
    // 2+ total accessors of cache_res, writer mode, no timeout -> REL383
}
```

### GRAMMAR-DATA CEILING, HONESTLY

No new `strata-core` grammar is added or needed: `_starvation.py` reads
only T-0700's `access`/`resource` grammar and T-0702's `users`/`rate`
grammar, both already surfaced. There is deliberately no "holding time"
clause in the grammar -- `Capacity.service_rate` (already a rate, i.e.
1/time) stands in as the holding-time hint for a DECLARED capacity; an
UNDECLARED capacity falls back to a fixed, conservative default (10ms
holding time / 100 per-second capacity, module docstring), never to an
unbounded one. `timeout` (REL383) is the same presence-only bare Node
attr string as `_reliability.py`'s Flow-scoped `timeout` -- independent
grammar site, deliberately not imported (module docstring).

### Waiver channel

REL380/REL381/REL382/REL383 DO join `_waive.py::
MULTI_INSTANCE_WAIVER_FAMILIES` (a node can access more than one
resource, so a waive clause must name the specific resource via the
`RULE:RESOURCE_ID` sub-target convention):

```
node db : trusted {
    access "ledger" mode exclusive;
    waive "REL380:ledger" reason "sharding migration tracked in T-9910-followup" ticket "T-9910";
}
```

## REL39x: KERNEL-INTERFACE + PROCESS-BOUNDS (T-0960)

`_process_bounds.py::check_process_bounds_obligations` reads
`KernelModel.nodes` (no new kernel field, charter law 1) to find every
node marked `kernel_interface` (this node touches a syscall, procfs/sysfs
entry, or ioctl -- a kernel/userspace boundary) with an undischarged or
unproven interface-classification obligation, AND every node marked
`deployed_process` (this node models a process actually deployed to a
host) with an undischarged or unproven cgroup resource-bound obligation.
Filed while reconciling T-0958's `system-design.yaml` deferred rows
(SDC-13-EVERY-KERNEL-USERSPACE-INTERFACE-SYSCALL-PROCFS-SYSFS-ENTRY-IOCTL-
IS-CLASSIFIED-INT, SDC-13-EVERY-DEPLOYED-PROCESS-DECLARES-ITS-RESOURCE-
BOUNDS-CGROUP-LIMITS-CPU-MEMORY-IO-AND): two genuinely checkable,
previously-unbuilt obligations structurally identical in shape to
REL26x's queue-intake pair and REL31x's interactive-cost pair, just for a
different resource/trust dimension.

TWO independent obligation pairs, both NODE-scoped (a node has at most
one marker attr per pair and fires at most one missing/unproven finding
each -- single-instance-per-node, the same carve-out REL260/261 and
REL310/311 establish, NEITHER pair registered in `_waive.py::
MULTI_INSTANCE_WAIVER_FAMILIES`):

- **REL390 missing interface classification** -- a `kernel_interface`
  node with no `interface_classified` attr. Deny-by-default: an
  unclassified kernel/userspace interface has no declared trust boundary
  at all, so a syscall/procfs/ioctl surface can silently widen with
  nothing statically flagging that it was never triaged.
- **REL391 unproven interface classification** -- a node DOES declare
  `interface_classified`, but the T-0331 PROVABILITY CONSTRAINT forbids
  discharging it by bare declaration alone: the node must have at least
  one file bound to it (`_code_binding.py::bind_code`) containing a real
  classification-shaped token (a trust/access-mode marker, a kernel
  filter/allowlist construct). A node with no bound code at all is
  UNCHECKABLE, not unproven -- the same ceiling REL201/REL222/REL231/
  REL261/REL301/REL311 draw.
- **REL392 missing process resource bounds** -- a `deployed_process`
  node with no `cgroup_bounds` attr. Deny-by-default: a deployed process
  with no declared resource bound can consume unbounded host cpu/memory/
  io -- the same "no ceiling declared, no ceiling enforced" risk REL26x's
  queue population and REL31x's interactive-flow population already
  cover for their own resource dimensions.
- **REL393 unproven process resource bounds** -- a node DOES declare
  `cgroup_bounds`, but the T-0331 PROVABILITY CONSTRAINT forbids
  discharging it by bare declaration alone: the node must have at least
  one file bound to it containing a real cgroup/resource-limit-shaped
  token. Same UNCHECKABLE-not-unproven ceiling as REL391.

### Surface vocabulary

```
node open_procfs_entry : trusted {
    kernel_interface;         // touches a procfs/sysfs/syscall/ioctl surface
    interface_classified;     // discharges REL390; REL391 then checks bound code
}

node worker_service : trusted {
    deployed_process;         // this node is a deployed, long-running process
    cgroup_bounds;             // discharges REL392; REL393 then checks bound code
}
```

### GRAMMAR-DATA CEILING, HONESTLY

`kernel_interface`/`interface_classified`/`deployed_process`/
`cgroup_bounds` are all presence-only bare Node attrs (no numeric
magnitude -- the same digit-led-literal ceiling every other REL2xx/REL3xx
marker in this family discloses), so REL390-REL393 prove PRESENCE of a
declared obligation and its code-level evidence, not a specific
classification value or a specific numeric cgroup limit. This is a
STATIC declaration-and-proof check over strata's own host/deploy
vocabulary, not runtime kernel introspection -- it cannot observe an
actual running process's actual cgroup file or an actual syscall's
actual classification, only whether the declaration and its bound-code
evidence exist. REL391's and REL393's proof-against-code are syntactic
token scans over the node's bound source, not a semantic call-argument
binding -- the same "ship what current tooling supports" honesty line
REL201/REL222/REL231/REL261/REL301/REL311 already establish.

### Waiver channel

REL390/REL391/REL392/REL393 do NOT join `_waive.py::
MULTI_INSTANCE_WAIVER_FAMILIES`, same as REL260/REL261/REL310/REL311: a
node carries at most one `kernel_interface`/`deployed_process` marker
pairing and fires at most one finding per rule, so a bare-rule `waive`
clause names exactly one thing:

```
node legacy_ioctl_shim : trusted {
    kernel_interface;
    waive "REL390" reason "legacy shim, classification tracked in T-9910-followup" ticket "T-9910";
}
```

## REL39y: ABI-COMPAT-WINDOW + BOOT-ATTESTATION (T-0962)

`_supply_chain_boot.py::check_supply_chain_boot_obligations` reads
`KernelModel.nodes` (no new kernel field, charter law 1) to find every
node marked `compiled_artifact` (this node is a compiled binary/library
targeting a declared ABI/ISA) with an undischarged or unproven ABI/ISA
compat-window obligation, AND every node marked `boot_chain_stage` (this
node models a stage in a boot chain -- firmware, bootloader, kernel,
initrd) with an undischarged or unproven boot-chain-attestation
obligation. Filed while reconciling T-0958's `system-design.yaml`
deferred rows (SDC-13-A-DECLARED-ABI-ISA-TARGET-IS-STABLE-ACROSS-A-
COMPATIBILITY-WINDOW-A-COMPILED-ARTIFA,
SDC-13-EVERY-BOOT-CHAIN-STAGE-IS-SIGNED-SECURE-BOOT-OR-MEASURED-INTO-AN-
ATTESTABLE-LOG-MEA): two genuinely checkable, previously-unbuilt
supply-chain/OS obligations, structurally identical in shape to the
REL39x KERNEL-INTERFACE + PROCESS-BOUNDS family `_process_bounds.py`
(T-0960) just established -- rule ids continue that same REL39x block
(REL394-REL397) rather than opening a new REL4xx numbering.

TWO independent obligation pairs, both NODE-scoped (a node has at most
one marker attr per pair and fires at most one missing/unproven finding
each -- single-instance-per-node, the same carve-out REL260/261,
REL310/311, and REL390-REL393 establish, NEITHER pair registered in
`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`):

- **REL394 missing ABI/ISA compat-window declaration** -- a
  `compiled_artifact` node with no `abi_compat_window` attr.
  Deny-by-default: a compiled artifact with no declared compat window
  has no tracked boundary for when a caller's assumption about its
  ABI/ISA stops holding.
- **REL395 unproven ABI/ISA compat-window** -- a node DOES declare
  `abi_compat_window`, but the T-0331 PROVABILITY CONSTRAINT forbids
  discharging it by bare declaration alone: the node must have at least
  one file bound to it (`_code_binding.py::bind_code`) containing a real
  compat-window-shaped token (a semver/version-range guard, a
  symbol-versioning construct). A node with no bound code at all is
  UNCHECKABLE, not unproven -- the same ceiling REL201/REL222/REL231/
  REL261/REL301/REL311/REL391/REL393 draw.
- **REL396 missing boot-chain attestation** -- a `boot_chain_stage` node
  with no `boot_attested` attr. Deny-by-default: an unattested
  boot-chain stage has no cryptographic or measured record that it ran
  as expected, so a compromised stage inserted ahead of it is
  undetectable by design.
- **REL397 unproven boot-chain attestation** -- a node DOES declare
  `boot_attested`, but the T-0331 PROVABILITY CONSTRAINT forbids
  discharging it by bare declaration alone: the node must have at least
  one file bound to it containing a real signing/measurement-shaped
  token (a secure-boot/signature-verification construct, a measured-boot/
  TPM/PCR construct). Same UNCHECKABLE-not-unproven ceiling as REL395.

### Surface vocabulary

```
node auth_library : trusted {
    compiled_artifact;    // a compiled binary/library targeting a
                           // declared ABI/ISA
    abi_compat_window;     // discharges REL394; REL395 then checks bound code
}

node bootloader_stage : trusted {
    boot_chain_stage;      // this node is a boot-chain stage
    boot_attested;          // discharges REL396; REL397 then checks bound code
}
```

### GRAMMAR-DATA CEILING, HONESTLY

`compiled_artifact`/`abi_compat_window`/`boot_chain_stage`/
`boot_attested` are all presence-only bare Node attrs (no numeric
magnitude -- the same digit-led-literal ceiling every other REL2xx/REL3xx
marker in this family discloses), so REL394-REL397 prove PRESENCE of a
declared obligation and its code-level evidence, not a specific ABI
version string or a specific signature/measurement algorithm. This is a
STATIC declaration-and-proof check over strata's own host/deploy
vocabulary, not runtime kernel or firmware introspection -- it cannot
observe an actual compiled artifact's actual ABI surface or an actual
boot chain's actual measurement log, only whether the declaration and
its bound-code evidence exist. REL395's and REL397's proof-against-code
are syntactic token scans over the node's bound source, not a semantic
call-argument binding -- the same "ship what current tooling supports"
honesty line REL201/REL222/REL231/REL261/REL301/REL311/REL391/REL393
already establish.

### Waiver channel

REL394/REL395/REL396/REL397 do NOT join `_waive.py::
MULTI_INSTANCE_WAIVER_FAMILIES`, same as REL260/REL261/REL310/REL311/
REL390-REL393: a node carries at most one `compiled_artifact`/
`boot_chain_stage` marker pairing and fires at most one finding per
rule, so a bare-rule `waive` clause names exactly one thing:

```
node legacy_bootloader_stage : trusted {
    boot_chain_stage;
    waive "REL396" reason "legacy stage, attestation tracked in T-9910-followup" ticket "T-9910";
}
```

## See also

- `docs/strata/host.md#resource-contention-sys2xx-t-0699` -- the SYS2xx
  sibling family this module mirrors.
- `docs/strata/boundary.md#crash-contracts-and-error-totality-adjacent-claims`
  -- T-0074's narrower, magnitude-aware no-hang check.
- `src/frob/strata/_reliability.py` -- `check_reliability_timeouts`,
  `check_reliability_health`, `ReliabilityViolation`, `ReliabilityReport`,
  REL200/REL201/REL210/REL211.
- `src/frob/strata/_retry.py` -- `check_retry_obligations`,
  `RetryViolation`, `RetryReport`, REL220/REL221/REL222.
- `src/frob/strata/_circuit_breaker.py` -- `check_circuit_breaker_obligations`,
  `CircuitBreakerViolation`, `CircuitBreakerReport`, REL230/REL231,
  `is_external_dependency`, `is_critical_dependency`.
- `src/frob/strata/_fallback.py` -- `check_fallback_obligations`,
  `FallbackViolation`, `FallbackReport`, REL240/REL241.
- `src/frob/strata/_spof.py` -- `check_spof`, `SpofViolation`,
  `SpofReport`, REL250.
- `src/frob/strata/_ssot.py` -- `check_ssot_obligations`, `SsotViolation`,
  `SsotReport`, REL290/REL291.
- `src/frob/strata/_txn.py` -- `check_txn_boundary_obligations`,
  `TxnBoundaryViolation`, `TxnBoundaryReport`, REL300/REL301.
- `src/frob/strata/_process_bounds.py` -- `check_process_bounds_obligations`,
  `ProcessBoundsViolation`, `ProcessBoundsReport`, REL390/REL391/REL392/
  REL393.
- `src/frob/strata/_supply_chain_boot.py` --
  `check_supply_chain_boot_obligations`, `SupplyChainBootViolation`,
  `SupplyChainBootReport`, REL394/REL395/REL396/REL397.
- `src/frob/strata/_obligation_proof.py` -- the shared proof-against-code
  plumbing REL22x/REL23x/REL24x reuse (not used by REL25x, module
  docstring: no proof-against-code needed for a structural fact).
- `tests/unit/strata/test_reliability.py` -- the REL200/REL201/REL210/
  REL211 firing/clean/waived/uncheckable litmus and unit coverage.
- `tests/unit/strata/test_retry.py` -- the REL220/REL221/REL222 firing/
  clean/waived/uncheckable unit coverage.
- `tests/unit/strata/test_circuit_breaker.py` -- the REL230/REL231
  firing/clean/waived/uncheckable unit coverage.
- `tests/unit/strata/test_fallback.py` -- the REL240/REL241
  firing/clean/waived/uncheckable unit coverage.
- `tests/unit/strata/test_spof.py` -- the REL250 firing/clean/waived
  unit coverage.
- `tests/unit/strata/test_ssot.py` -- the REL290/REL291
  firing/clean/waived/uncheckable unit coverage.
- `tests/unit/strata/test_txn.py` -- the REL300/REL301
  firing/clean/waived/uncheckable unit coverage.
- `tests/unit/strata/test_process_bounds.py` -- the REL390/REL391/
  REL392/REL393 firing/clean/waived/uncheckable unit coverage.
- `tests/unit/strata/test_supply_chain_boot.py` -- the REL394/REL395/
  REL396/REL397 firing/clean/waived/uncheckable unit coverage.
