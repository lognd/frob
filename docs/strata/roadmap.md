# strata roadmap -- phases, exit criteria, litmus program, ticket map

<!-- frob:ticket T-0048 -->

One sentence: six sequential phases, each with a hard exit criterion and a
frob ticket subtree (epic T-0047); the litmus models are permanent golden
fixtures that every language change must keep expressible and firing.

## Phases and exit criteria

| Phase | Parent | Contents | Exit criterion |
|---|---|---|---|
| 0 kernel + prover | T-0049 | six primitives, fact base, closure, claim evaluation (T-0055..T-0057) | hand-written payments kernel facts reproduce the golden findings with counterexample paths and quantifier-tagged verdicts (T-0058) |
| 1 surface v0 | T-0050 | parser, elaborator + std.trust, assert/assume + expiry, refinement (T-0059..T-0062) | `design/litmus/payments.strata` reproduces phase-0 goldens end to end in CI (T-0063, met) |
| 2 infra + policy | T-0051 | std.infra, age/staleness propagation, capacity + skew + horizons, five policy forms, analyzable pack + enables cascade, six-phase boundaries + frames, errors/observe packs, strata-core crate (T-0064..T-0071) | tube + chirp goldens fire: stampede, immutable-TTL pairing, CDN declassification, fanout ceiling under skew (T-0072) |
| 3 scenarios | T-0052 | scenario engine, crash contracts + no-hang, atomic/saga + fault-injection generation, breach blast radius + recovery-path independence (T-0073..T-0076) | Breach(Gateway) in the payments litmus yields blast radius, revocation/detection SLAs, and independence verdicts |
| 4 code binding + self-host | T-0053 | .strata as 6th frob.lang grammar, code globs + import conformance, effect extraction vs may-capabilities, directives + SYS gates (T-0077..T-0080) | `design/frob.strata` exists and frob gates on its own declared architecture (T-0081) |
| 5 applications | T-0054 | std.secrets, std.deploy, `frob sys plan` ticket compiler, `frob sys doc` + DOC002 claims audit, exporters (T-0082..T-0086) | a refuted claim files scoped tickets idempotently; a sys ticket cannot close until its claim discharges at the required rung |

Phase parents are chained with `blocked_by`, so `frob ticket doable`
always surfaces work in proof-dependency order.

<!-- frob:invariant INV-032 -->

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
  blast radius and recovery-path independence. Phase 1 exit (T-0063) is
  met: `design/litmus/payments.strata` (naive) and
  `design/litmus/payments_hardened.strata` (every remedy applied) are the
  surface-syntax twins of the phase-0 kernel-facts model, with goldens
  enforced in CI by `tests/unit/strata/test_litmus_surface.py`.
- **tube.strata** (video platform; phase 2, met T-0072): cold-cache
  stampede shape (high-rate watch flow with fanout into a write path);
  `staleness unlimited` legal only on the immutable content-addressed
  origin blob (a commented-out mutable variant, and a hand-built naive
  twin exercised directly in `tests/unit/strata/test_litmus_tube.py`,
  show the illegal/unsafe cases); CDN TLS termination as declassification
  (session data must not ride the CDN path -- proves only because
  `tls_terminates_at_provider` adds the declassify boundary; the naive
  twin without it refutes with the sessions -> origin -> edge witness);
  a money-grade payout node fed only through a 5-minute-stale approximate
  view-count cache, whose AGE bound refutes at 300.0s > 60.0s. Goldens
  enforced in CI by `tests/unit/strata/test_litmus_tube.py`.
- **chirp.strata** (timeline fanout; phase 2, met T-0072): a sharded hot
  shard fed via a `fanout 5` write-amplification path off the `tweets`
  store, with `skew zipf 1.5` -- the UTILIZATION bound refutes at the
  hottest shard (89.8%) where a byte-for-byte mean-based twin (no `skew`
  attr, identical demand/capacity) proves at 37.5%, the "averages lie"
  golden; a third shard's utilization claim, PROVED today, flips to
  REFUTED under `growth 10 %` compounding, saturating in 2 months --
  inside the 24-month deny-by-default horizon. Goldens enforced in CI by
  `tests/unit/strata/test_litmus_chirp.py`.

Growth candidates (post-phase-5): a WhatsApp-shaped model (E2E encryption:
`noflow(MessageBody -> Server)` with the server as a non-recipient) and a
search-shaped model (batch index pipelines with freshness lag).

## Self-hosting commitments (decision D7)

- This effort is tracked in frob tickets from day one: T-0047..T-0086.
- Phase 4 exit MET (T-0081): `design/frob.strata` declares frob's own
  architecture -- originally 8 components rolled up from the repo's 25+
  leaf packages (cli/app layer, graph+lang, gates, check, strata,
  dup+frob-core, vet, plus the `registry` foreign node vet talks to over
  the network); T-0707 added `registry_model` and `fleet`, and T-0440
  split `deploy`/`serve`/`mutate` off the former dup+frob-core utility-hub
  node into three standalone components with their own `may`/effects
  declarations (13 components today, dup+frob-core now narrower: dup,
  logging, process, gitlog, gitio, xref, outline, map, exports, perf,
  policy, release, scaffold, stats, bind, docs, fuzz, cycle, testing, cve,
  clean, render), the tickets ledger as an `append_only` git-tracked
  `store`, and the `.frob/` symbol-graph cache as a `cache` derived from a
  `graphlang` parse -- and `frob check --only sys` enforces it at zero
  violations, superseding the informal dependency diagram in
  `docs/rework.md` as enforced truth. Every flow in the model is a real
  cross-package import this repo has today (walked directly, not
  aspirational). Three claims prove: `c_no_registry_ledger` (supply-chain
  noflow from vet's network fetch to the ticket ledger, held by the
  `b_vet_endorse` boundary at `src/frob/vet/_registry.py::
  _result_from_network`), `c_cache_derivable` (the symbol-graph cache's
  age is bounded), and `c_gates_reach_tickets` (the gate suite's findings
  can reach the layer that writes the ledger). Locked in CI by
  `tests/system/test_frob_self_model.py`.
  - Grammar gap found while writing the model: the surface language's
    `code=<glob>` (docs/strata/surface.md#code-binding-tier-2-v0-
    implementation) and `may <capability>` (T-0079) are unreachable from
    `.strata` source text today -- `strata-core`'s lexer only accepts
    `[A-Za-z_][A-Za-z0-9_]*` IDENT tokens and `attr KEY=VAL` requires a
    single IDENT value, so a glob like `src/frob/app/**` cannot be
    written as an attr. Both features currently only work via a
    hand-built `KernelModel` in Python (exactly how their own test
    suites exercise them). Tracked as follow-up work, filed alongside
    this ticket's Done report.
- Phase 5: `frob sys plan` files strata's own remaining work as tickets --
  the language plans its own completion.
- T-0700 shipped access-modes + `resource`/`arbitrated_by` grammar
  (docs/strata/host.md#resource-access-modes-t-0700); `cli`/`gates`/
  `fleet`/`core`/`serve`'s five `SYS203:tickets_ledger` waivers (written
  "re-evaluate at T-0700") were re-pointed to the tracked follow-up
  (`frob:ticket T-0956` on each node) that will re-express the
  ledger's real single-writer-lock arbitration with the new grammar and
  drop the waivers once discharged -- not done in the same pass as the
  grammar ticket itself (design/frob.strata was out of that ticket's
  declared scope beyond the close-time live-tracker re-point).

## Ticket map

Epic: T-0047. Charter: T-0048 (this doc tree). Phase parents:
T-0049..T-0054 (chained). Children: phase 0 = T-0055..T-0058 (chained);
phase 1 = T-0059..T-0063; phase 2 = T-0064..T-0072; phase 3 =
T-0073..T-0076; phase 4 = T-0077..T-0081; phase 5 = T-0082..T-0086.
`frob ticket show <id>` for scope and acceptance; `frob ticket doable`
for the current frontier.
