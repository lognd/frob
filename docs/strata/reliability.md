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
