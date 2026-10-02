# grimble: the system-design model and its code binding

Status: DRAFT (T-0001, a v1-format id that migrates with an alias). Ownership after products.md: this is the grimble model (v1 name: strata), crates `grimble-model`, `grimble-kernel`, `grimble-bind`. Inputs: notes/v1/strata.md (surface grammar,
kernel, 12 binding mechanisms, rule inputs, measured adoption), the
binding requirement in goals.md, code-model.md.

Milestone 2 or later (D36): this whole file.

## 1. What the grimble model is, in one sentence

A typed architecture graph (nodes, flows, boundaries, claims, and a
V-model of requirements, designs, tests) whose elements bind to code
SYMBOLS in any language, checked by a small semantic kernel, with every
optional vocabulary (threat catalogs, reliability markers, compliance,
hosts) loaded as data packs rather than grammar.

Measured v1 adoption drives the cut: every consumer uses node, flow,
code, may, assert/assume, waive (now the exception kinds); two use the V-model; zero use policy,
scenario, refine, entity/architecture/configuration, host, Kerberos,
deploy, or the six-phase boundary grammar. 79 of 139 v1 keywords never
reached the prover.

## 2. Core grammar (kept, tightened)

```
module frob                              // root file; `part of frob` for fragments

node cli : trusted {
  clearance Internal;
  owns "crates/frob/**";                 // selector list (section 4)
  owns "crates/frob-check/src/lib.rs::run";
  may fs.read, fs.write at "crates/frob/**";
  may net.connect:api.github.com at "crates/frob-gh/src/lib.rs::GhClient.*";
  excuses net.listen reason "a CLI never serves";
  surface pub fn *, "Cli";                // intended public API, subset-checked
  attr timeout = 30 s;                    // typed attrs: number+unit | ident | string
}

store ledger : trusted { engine git_tracked; append_only; owns "tickets/**"; }

flow f_parse : cli -> symbols {
  label Internal; rate 100 req/s;
  via producer "crates/frob-check/src/lib.rs::run"
      consumer "crates/gob-symbols/src/lib.rs::parse_file"
      contract "crates/gob-symbols/src/lib.rs::ParsedFile";
}

boundary b_vet endorse f_install : foreign -> trusted when "checksum_verified";

assert noflow registry -> vet;
assume "weakness:CWE-78:vet" noflow registry -> vet owner logan review 2026-10-15;

vmodel req_1 kind artifact level requirements ref "docs/req.md#REQ-1";
vmodel t_1  kind test level unit runnable "crates/x/tests/t.rs::parses";
vmodel t_1 verifies req_1;

accept SYS004 on cli because "docs/decisions/2026-10-02-bootstrap-path.md";
defer SYS005 on cli ticket 01J9QKX3M8Z4T7N2V5B6C0D1E2 reason "producer lands next cycle";
```

Changes from v1 grammar:

- `owns` replaces `code`: real path globs (`**` crosses dirs, `*` does
  not), optional `::qualname-glob`, optional kind filter. Most specific
  selector wins; equal specificity on one symbol is an error; unclaimed
  symbols are FOREIGN.
- `may` scopes are selectors (`at`), and argument constraints (`of`)
  are resolved from the call AST, not the first string on the line.
- `excuses ATOM reason "..."` is the explicit matrix exclusion.
- `surface` replaces `attr interface=[...]` lists.
- `flow ... via producer/consumer/contract` gives flows symbol-level
  endpoints; cross-language flows need no special syntax.
- Typed attrs (number with unit, ident, string, list) so markers carry
  magnitude. Units are types as in v1.
- Every construct has a stable id and the parser emits spans for all of
  them (v1 regex-located spans are gone).
- Multi-file from day one: `part of` fragments can declare anything,
  not only `extend node`.
- `waive` is replaced by the exception kinds of exceptions.md: `accept
  RULE on NODE because "..."`, `defer ... ticket ID reason "..."` and
  `hotfix ...`; `baseline` pools stay in `grimble-ratchet.lock.json`.
  The `ticket` value is opaque to grimble.

Dropped from grammar (available as data packs or not at all): host,
krb, deploy, cdn/balancer/queue/cache/secret/resource as keywords (they
become `node ... kind queue` with typed attrs), operation/saga/crash/
breach, six-phase boundary blocks, policy Tier-2, scenario, refine,
entity/architecture/configuration, carries (PII becomes a capability
pack), import/export/layer.

## 3. Kernel

Crate `grimble-kernel`, ported from the v1 strata kernel (Rust already): label closure over flows with
boundary endorse/declassify, SCC longest-path age, summed demand and
capacity utilisation, V-model closure (paired levels, five structural
rules, milestone known gaps), claim verdicts PROVED / REFUTED(witness) /
UNPROVABLE with auto-generated assumes, assume ownership and expiry.
Everything else is a join between the model and the code graph.

## 4. Binding (the point of the exercise)

Model side declares intent and ceilings; code side carries sparse
attestations; neither side is ever auto-regenerated to match the other
(the v1 "never auto-widen" lesson). Shrink-only automation is allowed
(`grimble shrink` removes grants never observed, with a reason).

| Declared | Where | Resolves to |
|---|---|---|
| `owns SELECTOR` | node, store | set of symbols (code-model.md section 2 addresses) |
| `may ATOM at SELECTOR of CONSTRAINT` | node | capability grant scoped to symbols |
| `excuses ATOM reason` | node | matrix cell `excused` |
| `surface SELECTOR` | node | intended public symbols |
| `flow via producer/consumer/contract` | flow | three symbols, any languages |
| `vmodel ... ref / runnable` | vmodel | doc anchor or test symbol |
| `grimble:node N`, `grimble:channel F role=producer`, `grimble:boundary B`, `grimble:effect ATOM because "..."` | code comments (grimble namespace; frob never reads them) | attestations checked against the model |

Drift findings (all computed from the code graph and the model on every
check; each is one generated rule in `grimble-bind` or
`grimble-capabilities`). Ids are `FAMILYNNN` with a slug alias, the same
grammar as every other product (v1's 51 SYS ids collapse many-to-one
into these; rules.md section 3):

| Id | Alias | Condition |
|---|---|---|
| SYS001 | SYS-UNRESOLVED | selector matches zero symbols |
| SYS002 | SYS-AMBIGUOUS | symbol claimed by two equally specific selectors |
| SYS003 | SYS-UNMODELED | symbol with effects or public visibility claimed by no node; evaluated only for selectors listed in `[grimble] modeled` in `grimble.toml` (opt-in, not a repo-wide Warn) |
| CAP001 | CAP-EXCEEDS | observed capability at a symbol with no covering grant (the v1 SYS100); Error |
| CAP002 | CAP-STALE | grant never observed at its scope (shrink-only fix); Warn |
| CAP003 | CAP-UNEXCUSED | capability atom applicable to the node's languages, neither granted nor excused; Advisory for one release after a new atom or detector ships, then Warn |
| SYS004 | SYS-UNDECLARED-FLOW | import or call edge between two owners with no flow in that direction (v1 SYS003, now every language) |
| SYS005 | SYS-UNIMPLEMENTED-FLOW | flow declared, producer or consumer selector empty |
| SYS006 | SYS-CONTRACT-SKEW | contract symbol fingerprint differs between the producer and consumer acks recorded with `grimble ack` in `grimble.lock` |
| SYS007 | SYS-CHANGED | bound symbol's body digest changed since the last `grimble ack` in `grimble.lock` (the same mechanics as `frob.lock` from `gob-lock`, a separate file) |
| SYS008 | SYS-RENAMED | bound symbol vanished, same-digest symbol appeared elsewhere (suggest, never edit) |
| SYS009 | SYS-SURFACE | public symbol outside `surface` |

grimble has its own `ack` verb and `grimble.lock`; it never reads
`frob.lock`, and frob never reads `grimble.lock`.

Capability observation moves from substring needles to typed call-site
detectors (IR patterns plus resolved callee), held in a data registry
with v1's row schema (language, library, pattern, capability, cwe,
rationale, safer alternative, severity). A language without a detector
for an atom reports that cell as `n/a`, and the summary carries one
Unresolved per node (not per cell) so an unmeasured node never reads as
clean.

Cross-language flows: FFI, IPC, and HTTP edges are never inferred from
text. They are declared flows with a contract symbol; the check is
"producer exists, consumer exists, contract fingerprint acknowledged on
both sides". Where a `binds` edge exists (code-model.md section 6) the call graph
crosses it, so a Python handler calling a Rust kernel through PyO3 is
one resolved edge and an undeclared flow is caught.

## 5. Data packs

Threat obligations (capability -> obligation discharged by a claim at a
rung), reliability markers (one "marker plus evidence" rule shape, not
51 REL ids), compliance views, CVE fingerprints, and PII categories ship
as TOML packs under `packs/` and are enabled per repo in `grimble.toml`
(`[grimble] packs = ["threat", "reliability"]`). Milestone 2 or later
(D36). A pack contributes
capability atoms, detectors, obligations, and rule parameters; it never
contributes grammar.

## 6. Registry drift-lock

Kept in spirit: a registry row names a concept and its disposition
(`handled_by RULE`, `deferred ticket=<ulid>` with the ticket opaque to
grimble, `duplicate_of`, `out_of_scope caught_by`). In v2 the registry is generated from rule metadata plus
pack data, and the only hand-written part is dispositions for concepts
with no rule yet. Rows whose deferred ticket closes go red, as in v1.

## 7. What frob gets from this (grimble never knows about tickets)

- Tickets link to grimble entities with an `implements` link
  (`design:node/cli`); frob validates the target only through
  `grimble graph --json` (Unresolved when grimble is absent). An epic can
  be "implement flow f_parse", and the flow's SYS005 finding closes when
  the ticket lands.
- Exceptions that name a ticket (`defer`, `hotfix`): grimble parses the
  `ticket=` value as opaque and emits it in `--json`; standalone grimble
  reports such an exception as Unresolved-exit, and frob evaluates the
  exit and the close guard from that JSON (exceptions.md section 2).
- The V-model is the requirements-to-tests traceability Jira lacks:
  requirement -> design decision -> ticket -> test, all symbols, all
  checked.
- `grimble status` renders the model with per-node drift counts;
  `grimble graph --dot|--json` exports it; the frob GUI (gui.md) shows
  the same through grimble's `--json`.

## 8. Open questions

Decided 2026-10-02: `.grmb` is its own language with its own parser
(leaf crate, spans for every construct, JSON export on day one, editor
grammar generated from the keyword table); FOREIGN symbols are Warn
until `[grimble] strict = true` in `grimble.toml`.
