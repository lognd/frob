# Extending frob: registry guides

Every registry/extension point in frob is documented here on a common
template, one guide per registry (T-0159). This is the answer to "I want
to add a new X" for any X frob knows how to catalog.

## Common template

Each guide below follows the same shape:

1. **What / where** -- the registry's purpose, its file path(s), and the
   exact symbol name(s) that hold it.
2. **Add-an-entry recipe** -- the concrete edit(s) to make, in order.
3. **Drift-locks that fire** -- which gate/test enforces completeness when
   you add (or fail to add) an entry, and exactly what each demands.
4. **Worked example diff** -- a realistic sketch of adding one new entry.
5. **Common mistakes** -- real incidents from this repo's ticket history,
   cited so the same mistake is not repeated.

## The registry-of-registries

[`registry_of_registries.json`](registry_of_registries.json) is the
machine-readable inventory this guide series is generated from -- one
entry per registry, naming its guide file and the code symbol a
`frob:doc`/`frob:describes` anchor binds it to.
`tests/unit/test_extending_guides_complete.py` is the anti-rot mechanism:
it asserts every entry has a guide file under this directory AND a live
anchor pointing at that guide on its named `anchor_file`/`anchor_symbol`.
**Adding a new registry without adding a guide and an anchor fails the
build.**

## The guides

- [Gate rule families](gate-rule-families.md) -- COV/TEST/DRIFT/SCOPE/PRE/DOC/PERF/SYS/WAIVE/...
- [Comment DSL directives](comment-dsl-directives.md) -- `frob:ticket`/`tests`/`doc`/`waive`/`todo`/`invariant`/`channel`/`boundary`/`secret`
- [Threat catalog](threat-catalog.md) -- `std.cwe` weaknesses, out-of-scope entries, benign capabilities, THREAT001-006
- [Compliance registry](compliance-registry.md) -- regulations, COPPA/GDPR/HIPAA-style checks
- [Capability registry](capability-registry.md) -- dangerous operations, per-language matrix
- [CVE fingerprints](cve-fingerprints.md) -- CVEFP001
- [PII categories](pii-categories.md) -- PII001-004
- [Design-lint rules](design-lint-rules.md) -- LINT001-005
- [Secrets-scan providers](secrets-scan-providers.md) -- the ALL_PROVIDERS drift-lock
- [Prover claim kinds](prover-claim-kinds.md) -- NoFlow/Reach/BoundClaim/Independent/SetEquality
- [Scenario kinds](scenario-kinds.md) -- RemoveNode/ScaleRate/SetTrust/AddFlow rewrites
- [Strata surface grammar](strata-surface-grammar.md) -- keywords + the tmLanguage drift-lock
- [`[[test.runner]]` entries](test-runner-entries.md) -- frob.toml test routing
- [Language grammar handlers](language-grammar-handlers.md) -- the `_WALKERS` dispatch
- [sys export formats](sys-export-formats.md) -- k8s/seccomp/iam
- [Litmus fixtures](litmus-fixtures.md) -- `.strata` test-data mapping
- [Ticket kinds/states](ticket-kinds-states.md) -- `TicketKind`/`TicketState`/`Stride`/`Origin`
- [Benign capabilities](benign-capabilities.md) -- THREAT002 `may`-kind excuses
- [Dup detector registry](dup-detector-registry.md) -- the R1-R7 rung ladder, DUP001/DUP002/DUP003

## Known gaps (filed, not silently fixed)

A few registries in this series (prover claim kinds, scenario kinds,
`sys` export formats) have NO automated drift-lock tying "a new variant
exists in the model" to "a dispatch arm handles it" -- the failure mode is
a runtime unhandled-variant error, not a `frob check` gate. Each affected
guide calls this out under its own "Drift-locks that fire" section. Filed
as follow-on hardening work rather than fixed here (T-0159's scope is
documentation plus doc anchors, not new gate rules); see `tickets.md` for
the filed ticket ids.
