# strata roadmap -- phases, exit criteria, litmus program, ticket map

<!-- frob:ticket T-0048 -->

One sentence: six sequential phases, each with a hard exit criterion and a
frob ticket subtree (epic T-0047); the litmus models are permanent golden
fixtures that every language change must keep expressible and firing.

## Phases and exit criteria

| Phase | Parent | Contents | Exit criterion |
|---|---|---|---|
| 0 kernel + prover | T-0049 | six primitives, fact base, closure, claim evaluation (T-0055..T-0057) | hand-written payments kernel facts reproduce the golden findings with counterexample paths and quantifier-tagged verdicts (T-0058) |
| 1 surface v0 | T-0050 | parser, elaborator + std.trust, assert/assume + expiry, refinement (T-0059..T-0062) | `design/litmus/payments.strata` reproduces phase-0 goldens end to end in CI (T-0063) |
| 2 infra + policy | T-0051 | std.infra, age/staleness propagation, capacity + skew + horizons, five policy forms, analyzable pack + enables cascade, six-phase boundaries + frames, errors/observe packs, strata-core crate (T-0064..T-0071) | tube + chirp goldens fire: stampede, immutable-TTL pairing, CDN declassification, fanout ceiling under skew (T-0072) |
| 3 scenarios | T-0052 | scenario engine, crash contracts + no-hang, atomic/saga + fault-injection generation, breach blast radius + recovery-path independence (T-0073..T-0076) | Breach(Gateway) in the payments litmus yields blast radius, revocation/detection SLAs, and independence verdicts |
| 4 code binding + self-host | T-0053 | .strata as 6th frob.lang grammar, code globs + import conformance, effect extraction vs may-capabilities, directives + SYS gates (T-0077..T-0080) | `design/frob.strata` exists and frob gates on its own declared architecture (T-0081) |
| 5 applications | T-0054 | std.secrets, std.deploy, `frob sys plan` ticket compiler, `frob sys doc` + DOC002 claims audit, exporters (T-0082..T-0086) | a refuted claim files scoped tickets idempotently; a sys ticket cannot close until its claim discharges at the required rung |

Phase parents are chained with `blocked_by`, so `frob ticket doable`
always surfaces work in proof-dependency order.

## CLI surface (target)

```
frob sys check                    # parse + elaborate + prove + report
frob sys trace <from> <to>        # show the closure path(s)
frob sys capacity [--population N | --at DATE]
frob sys threats [boundary]       # STRIDE checklist generated per boundary
frob sys plan                     # obligations -> tickets (idempotent)
frob sys doc                      # generated reference + mermaid topology
frob sys export --k8s-netpol|--seccomp|--iam
```

## The litmus program (`design/litmus/`, golden-tested in CI)

Litmus models are the language's compiler test suite: tracked fixtures
with expected-findings files (decision D4). Each stresses a different
profile, and each finding corresponds to a real production outage or
vulnerability class:

- **payments.strata** (Stripe-shaped; phases 0-1, extended in 3): foreign
  third-party response reaching state without endorsement; webhook
  at-least-once vs idempotency; refund decision reading a stale replica
  (freshness mismatch = the double-refund class); breach scenario with
  blast radius and recovery-path independence.
- **tube.strata** (video platform; phase 2): cold-cache stampede unless
  request coalescing is declared; `staleness unlimited` legal only on
  immutable content-addressed blobs; CDN TLS termination as
  declassification (session data must not ride the CDN path);
  approximate view counter feeding a money-grade payout flow.
- **chirp.strata** (timeline fanout; phase 2): materialized-timeline write
  amplification under zipf skew -- the per-key ceiling failure whose forced
  remedy is the fanout-on-write/read hybrid; hot-shard capacity checked at
  the hottest key, not the mean.

Growth candidates (post-phase-5): a WhatsApp-shaped model (E2E encryption:
`noflow(MessageBody -> Server)` with the server as a non-recipient) and a
search-shaped model (batch index pipelines with freshness lag).

## Self-hosting commitments (decision D7)

- This effort is tracked in frob tickets from day one: T-0047..T-0086.
- Phase 4 exit: `design/frob.strata` declares frob's own architecture
  (module dependency direction, trust of inputs, the gitio subprocess
  seam, tickets/lock as tracked truth) and `frob check` enforces it,
  superseding the informal dependency diagram in `docs/rework.md` as
  enforced truth.
- Phase 5: `frob sys plan` files strata's own remaining work as tickets --
  the language plans its own completion.

## Ticket map

Epic: T-0047. Charter: T-0048 (this doc tree). Phase parents:
T-0049..T-0054 (chained). Children: phase 0 = T-0055..T-0058 (chained);
phase 1 = T-0059..T-0063; phase 2 = T-0064..T-0072; phase 3 =
T-0073..T-0076; phase 4 = T-0077..T-0081; phase 5 = T-0082..T-0086.
`frob ticket show <id>` for scope and acceptance; `frob ticket doable`
for the current frontier.
