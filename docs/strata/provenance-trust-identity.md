# Provenance and trust-as-identity (T-3961)

Standalone doc row for T-3961's accepted design and its implementation
(T-4612). Filed as a standalone file rather than folded into
`docs/modules/gates.md` because that file was leased by another
in-progress ticket (T-4111) at implementation time -- fold this section
in there once that lease clears, rather than duplicating it permanently.

## Background

F-273 (a raw client IP trusted behind a proxy, confirmed threat-model
finding): a wrong client IP is still just a string, so nothing in strata
could say "this value must come from exactly one helper". T-3961's
design note (parent ticket, see its Done report) investigated existing
mechanisms first and concluded both new constructs below reuse the
existing `Node.attrs` opaque-attr slot -- the SAME attr-desugar
convention `code=`/`pii=`/T-4073's `no_pii` already use. Zero
`strata-core` grammar change, zero new `KernelModel` field.

## `derived_from:<tag>=<helper>`

An attr on a node that ALSO `carries` the PII tag `<tag>`
(`frob.strata._pii.PII_CATEGORIES`-shaped, e.g. `identifier.client_ip`),
naming `<helper>` (a qualified symref, the same dotted convention
`frob:doc`/`frob:tests` already use) as the SOLE legitimate producer of
values assigned to that tag.

```
node gateway {
    trust = trusted
    attr "pii=identifier.client_ip"
    attr "derived_from:identifier.client_ip=app.net.get_trusted_client_ip"
}
```

Parsing/joining: `frob.strata._pii.node_derived_from`.

**PII005** (`frob.strata._pii.check_pii_derived_from_contradiction`):
two `derived_from:<tag>=<helper>` attrs naming the SAME tag with
DIFFERENT helpers on the same node is a contradiction ("which one
actually produces it" cannot both be true) -- deny-by-default, the same
shape PII001 takes on a malformed declaration.

**SYS116** (`frob.gates._sys_provenance.check_undeclared_provenance`):
a node `carries` an `identifier.*` tag with NO matching `derived_from`
attr at all -- the F-273 finding itself. Narrowed to the `identifier.*`
category (not all seven `PII_CATEGORIES`) to avoid a mass false-positive
wave across every already-declared `contact`/`financial`/etc. tag in
this repo's own `design/` on first landing; widening the category set is
real future work, not required for SYS116's cheap first step.

## `trust_identity:<tag>`

An attr on a node declaring it AUTHORIZED to treat a value under the
named PII tag as a trusted identity fact (used in an
authorization/audit-log/rate-limit decision), as opposed to merely
holding or forwarding it. This is a DIFFERENT axis from `may` capability
(a node can have `net.in` capability and carry the tag while declaring
NO `trust_identity` attr for it -- meaning it may receive and hold the
value, but treating it AS identity is undeclared).

```
node auth {
    trust = trusted
    attr "pii=identifier.client_ip"
    attr "trust_identity:identifier.client_ip"
}
```

Parsing: `frob.strata._pii.node_trust_identity_tags`.

**SYS117** (`frob.gates._sys_provenance.check_trust_identity_without_carries`):
a `trust_identity:<tag>` attr naming a tag the node does NOT itself
`carries` is a contradiction -- a provenance statement about data the
node's own model says it does not hold.

## SYS10x consumer

`frob.gates._sys_provenance.evaluate_provenance` runs SYS116 + SYS117
over a `KernelModel` and returns `frob.gates._models.Violation`s
(gate-shaped, distinct from `frob.strata._pii.PiiViolation`, mirroring
why `_sys_selfaudit.py` is split from `_selfconform.py`).

**Not yet wired** (disclosed, not silently dropped) into
`frob.gates._sys.sys_gate`'s dispatch or
`frob.gates._waive._KNOWN_GATE_RULES`'s rule-id registry: both files
were held by an in-progress ticket's lease (T-4212) at implementation
time. `frob:todo T-4612` marks this gap; a follow-up ticket
should wire `evaluate_provenance` into `sys_gate` and register
SYS116/SYS117 in `_KNOWN_GATE_RULES` once that lease clears.

## Open questions (carried from T-3961's design note, not resolved here)

- Node-level vs. flow-level `derived_from` (currently node-level, the
  cheap-first-step default, same as `carries` itself).
- Whether SYS116's structural cross-check (tracing the real assignment
  site to the named helper via `frob.lang`/`frob.xref`) should follow --
  explicitly deferred, same disclosure posture as PII013/T-4073's own
  taint-analysis deferral.
- Whether `trust_identity` should become a first-class kernel construct
  rather than an attr-string, if usage proves the cheap version
  insufficient.
