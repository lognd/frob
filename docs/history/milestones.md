# Milestone history

Status: historical
Owner: frob
Decisions: D36, D55
Audience: contributor

Provenance: collected under ~9TGBAW8 from sections cut out of the current design files (build-test-ci.md milestones, architecture.md section 1, products.md section 4). Text is kept as it was written; the current rules live in the files named in docs/design/README.md.

## 1. Milestone 1

Milestone 1 (D36) is: `frob check` and `frob land` run green on this
repository, with tickets in the v2 ledger, using the Rust, markdown and
TOML adapters only. There is no grimble, crunk, GUI, daemon, job store,
salsa, IR, PM forecasting or Jira-parity feature in it. Self-hosting
means frob alone: the self check does not merge sibling findings, and
the CI jobs below that mention grimble, crunk, bundling, macOS and
Windows packaging, benches and release are Milestone 2 or later (D36)
unless they say otherwise. The crate cut, with the verbs and rules each
crate brings, is the table at the end of notes/review/audit-design.md.

Status: the crates under `crates/` are `frob` (the binary, package
`frob-cli`), `frob-ack`, `frob-evidence`, `frob-lease`, `frob-ledger`,
`frob-obligations`, `frob-tests`, `frob-worktree`, `gob-cache`,
`gob-cli`, `gob-config`, `gob-dev`, `gob-diagnostics`, `gob-directives`,
`gob-exec`, `gob-git`, `gob-languages`, `gob-lock`, `gob-log`,
`gob-macros`, `gob-mdtest`, `gob-rules`, `gob-symbols`, `gob-text` and
`gob-walk`, plus `frob-check` and `frob-land`, which have landed (the
exact set is `ls crates/`). The self-host switch remains: `frob check`
and `frob land` run green on this repository only once it is made, and
until then the v1 `frob:waive DOC006` comments in the design files and
the `frob:waive DOC004` lines that gob-dev emits into generated rule
pages still fail DSL001; the switch converts both to `frob:accept ...
because="..."` (gob-dev emits the new form).

Milestone 1 carried no digest or lock decisions beyond scheme 1 (code-model.md
section 2); this repository's `frob.lock` is empty today.

## 2. Milestone 2

The single authoritative statement of milestone-2 order (D36 deferrals
included); monorepo.md section 5, universal-model.md section 8,
grimble/grmb-spec.md 20.2, docs/design/grimble/rule-families.md section 6 and migration.md point here.

1. The gob-diagnostics Unresolved gate fix (cli.md section 2): the
   landed `exit.rs` skips Unresolved findings; it gains the
   `[check] fail_on_unresolved` test, the `required` mark on the finding
   record and the three required cases. A ticket changes it before any
   sibling can be configured.
2. gob-ir: U terms, scope graph with status, canonical facet stream,
   queries, Kleene evaluator and answer lattice, the atom registry and
   callee vocabularies; the Rust and markdown adapters re-expressed over
   U in gob-symbols (universal-model.md section 8; gaps G1-G4 and
   G10-G19).
3. The digest scheme and typed lock (G05): canonical facet streams,
   facets Sig, Body, Doc, Attr and Contract, `digest_scheme` in
   gob-lock, typed `symbol | flow` entries, the ack planner moved to
   gob-lock. Open question 5 of universal-model.md (G9) is closed first.
   Consumer `frob.lock` import (migration.md) waits for this item; this
   repository's own `frob.lock` is regenerated at this point.
4. gob-check extraction (G06): the product-neutral pipeline, exception
   application moved to gob-rules, rule `polarity` and
   `subjects_examined`.
5. The grimble cut G01-G19 (notes/review/grimble-review.md section 5,
   critical path T-IR, G01, G02, G07, G08, G09, G11, G14): G01 .grmb
   specification, G02 binding semantics over U, G03 sibling JSON
   contract, G04 packs and drift-lock, G05 and G06 above, G07 selectors,
   G08 grimble-model parser and U adapter, G09 binary skeleton, G10
   grimble-arch (CYCLE, LARGE, DEAD), G11 and G12 grimble-bind, G13 frob
   orchestration of the sibling stage, G14 grimble-capabilities with the
   cell set of grimble/binding.md 7.5, G15 shrink, G16 kernel port, G17
   gob-pattern and GPOL (blocked by the ast-grep `Doc`-over-U spike,
   rules.md section 3), G18 (was `grimble migrate`; dropped, D136), G19 grimble-serve.
6. The first ten NEAT rules (docs/design/grimble/rule-families.md section 4), then
   `[neat] require_effects` for this repository's public surface.
7. The GitHub Actions and Dockerfile adapters and the CI and DK rules in
   grimble-ci (grimble/rule-families.md); the zizmor and actionlint `[[check.tool]]`
   stages with parsers in gob-check and id maps in frob-check land earlier and are
   adopted by this repository first.
8. PM enforcement (PM026 included) and the remaining D36 deferrals
   (grimble-vet, packs, SARIF, salsa, GUI, daemon, jobs, crunk).

## 3. Early workspace shape

Three binaries (`frob`, `grimble`, `crunk`) from one Cargo workspace,
strict downward dependencies, about 65 crates in four groups (D1 said
about 57 before D56-D60 added gob-check, gob-pattern, grimble-ci and
the gob-ir layering; boundaries.md section 4 has the count). The
authoritative capability-to-crate map is boundaries.md; the shape:

```
crates/
  gob-*        substrate, depends only on gob-*:
               text config languages symbols directives rules macros
               diagnostics fix walk cache git exec cli log lock serve
               mdtest dev; milestone 2 or later (D36): db (salsa), ir
               (the universal model, below symbols), check (shared
               pipeline), pattern (ast-grep-shaped engine)
  frob-*       ledger pm lease worktree evidence tests obligations ack land
               release fleet explore check gh hook serve
  grimble-*    model kernel bind capabilities lints arch security vet packs
               ci check serve
  crunk-*      values spec ingest tailwind rules tokens query gallery adapters
  frob, grimble, crunk     thin binaries
```

## 4. What moved where between the earlier files

| Earlier location | Now |
|---|---|
| code-model.md sections 5 (IR), 6 (binds), 7 (capabilities) | grimble (`grimble-lints`, `grimble-bind`, `grimble-capabilities`), with `gob-ir` (the universal model, D56) and `gob-symbols` (its adapters) providing U terms and symbols to all three |
| rules.md families CYCLE ARCH LARGE DEAD DUP SEC PII SYS CAP BIND GPOL | grimble |
| rules.md families DRIFT AFFECT COV TODO SCOPE PRE QUEUE INV TEST TDD DOC DOCENUM NEGEXIST REF TICK MILE DEPR REL VERSION REG DEC NARR POL PM, and the ticket-bound exits of EXC | frob (the authoritative table is boundaries.md section 2.5) |
| grimble/grmb-spec.md 20 | grimble's model |
| `frob check` | runs frob's gates and, when grimble or crunk is installed, runs their checks in-process (feature `bundle`) or via their `--json` and merges findings into one report through the shared `gob-rules` registry |
| v1 `vet` | grimble (`grimble-vet`): the capability model applied to dependencies |
| v1 `explore` verbs | both frob and grimble, as views over `gob-symbols` |

The shared registry means a waiver syntax, a severity model, a ratchet
pool, and a renderer serve all three products; `frob check` is the one
command an agent runs, and it reports `grimble` and `crunk` findings under
their own family prefixes.

The full capability-to-crate map, the placement test, and the splits
considered are in boundaries.md.
