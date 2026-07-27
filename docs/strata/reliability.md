# strata reliability family: REL2xx (T-0640, T-0644, T-0641, T-0642, T-0643, T-0645)

Home for the T-0331 systems-checks epic's reliability catalog line "TIMEOUT
on every remote/cross-boundary flow" -- the first REL2xx family to land.
Mirrors `docs/strata/host.md#resource-contention-sys2xx-t-0699`'s shape
deliberately: a rule module (`_reliability.py`), a `Report`/`Violation`
pydantic pair, the SAME T-0174 waiver channel, and `frob sys audit` CLI
wiring.

## REL2xx: TIMEOUT obligation (T-0640)

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

`timeout` is presence-only, no magnitude. `strata-core/src/parse.rs`'s
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
`strata-core/src/parse.rs`'s generic `attr KEY=VALUE` clause imposes on
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
