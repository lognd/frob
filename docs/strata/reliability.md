# strata reliability family: REL2xx (T-0640, T-0644)

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

## See also

- `docs/strata/host.md#resource-contention-sys2xx-t-0699` -- the SYS2xx
  sibling family this module mirrors.
- `docs/strata/boundary.md#crash-contracts-and-error-totality-adjacent-claims`
  -- T-0074's narrower, magnitude-aware no-hang check.
- `src/frob/strata/_reliability.py` -- `check_reliability_timeouts`,
  `check_reliability_health`, `ReliabilityViolation`, `ReliabilityReport`,
  REL200/REL201/REL210/REL211.
- `tests/unit/strata/test_reliability.py` -- the REL200/REL201/REL210/
  REL211 firing/clean/waived/uncheckable litmus and unit coverage.
