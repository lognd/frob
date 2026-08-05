# frob rework: the enforcement layer

One sentence: frob becomes the auditor of the agentic stack -- the tool that
makes it impossible for work to silently not happen -- by replacing its
retrieval-era commands with an obligation graph, a statically-checkable
ticket queue, and gates that make unaccounted-for work a build failure.

Division of labor: Serena (LSP/MCP) navigates code, Claude Code edits code,
frob accounts for code. frob owns durable cross-artifact claims (docs,
tickets, invariants, policy) and their enforcement; it no longer competes on
context retrieval or packing.

This is the umbrella document. Component designs:

- `docs/modules/graph.md` -- obligation graph engine, comment DSL, lock file, drift
- `docs/modules/tickets.md` -- ticket/feature queue, attachments, clipboard capture
- `docs/modules/gates.md` -- gates (drift, coverage, scope, pre-work), policy,
  invariants, `frob check` integration

## Architecture

Dependency direction is strictly downward; no module imports a module above it.

```
frob.lang        tree-sitter parsing: symbols + comments, 5 languages
   ^
frob.graph       symbol registry, digests, edges, DSL, lock file, drift
   ^
frob.gitio       the ONE git subprocess seam: repo root, diff, branch
                 (worktree-correct; leaf module beside frob.lang)
   ^
frob.tickets     ticket queue, attachments, clipboard   (peers, no
frob.policy      declarative rules over files/graph      cross-imports)
frob.testing     touched-set selection + per-language runner registry
   ^
frob.gates       drift/coverage/scope/pre-work/invariant/test/policy gates;
                 validates edge endpoints across graph and tickets
   ^
frob.check       aggregate quality gate (existing, extended)
```

Cycle avoidance (resolved at design time): `frob.graph` stores directive
targets (ticket IDs, doc anchors) as opaque strings and never validates
them; `frob.gates` is the only module that joins graph edges against ticket
and doc stores. This keeps graph <- tickets from ever forming a cycle.

Data at rest:

| Artifact | Location | Tracked | Owner |
|---|---|---|---|
| Code annotations (DSL) | source comments | yes | frob.graph |
| Doc anchors | `docs/**/*.md` HTML comments | yes | frob.graph |
| Acknowledgments | `frob.lock` (repo root) | yes | frob.graph |
| Tickets + attachments | `tickets/` | yes | frob.tickets |
| Invariants | `invariants/` | yes | frob.gates |
| Policy rules | `frob.toml` `[policy]` | yes | frob.policy |
| Derived index cache | `.frob/cache.db` | no (gitignored) | frob.graph |

Rule: nothing authoritative lives in `.frob/` -- it is gitignored and must
always be rebuildable from tracked text.

## Alpha purge (Phase 0)

This is an alpha; stale code is deleted outright. No deprecation shims, no
aliases, no migration paths.

Deleted commands and their modules, runners, docs, and tests:

- `edit` (Serena `replace_symbol_body` covers it)
- `dispatch`, `mission` (Claude Code subagents made them redundant)
- `todo` (replaced by `frob ticket`)
- `ctx`, `bundle`, `stub`, `tokens` (context economy -- commoditized;
  Serena + Claude Code native tools own this lane)
- `inspect` (PyCharm headless -- unused)
- `init` (deprecated alias of `scaffold`)

Kept (still earn their place; re-platform onto `frob.lang` opportunistically,
never as a blocker): `scaffold`, `map`, `outline`, `xref`, `parse`, `dup`,
`cycle`, `arch`, `bind`, `exports`, `docs`, `gitlog`, `check`. (Historical
snapshot: `map`/`outline`/`xref` were later deprecated, sunset 2026-10-01,
T-0580/T-0802; T-1238 (2026-08) rescinded that sunset and regrouped all
three, plus `frob docs --search`, under `frob explore` instead -- see
docs/design/cli-regrouping.md and docs/modules/cli.md.)

New commands: `frob graph`, `frob ack`, `frob ticket`, `frob test`
(touched-set cross-language test execution; see docs/modules/testing.md). Deferred
(post-alpha): `frob serve` (MCP adapter exposing enforcement queries).

`frob.ast` (Python + C++ only) survives Phase 0 because kept commands use it;
it is absorbed into `frob.lang` when those commands are re-platformed.

## Agents and skills redesign

Organizing values: security, thoroughness, interface auditing, proving what
matters, hierarchical decomposition. Every agent reads and writes the ticket
queue; no agent-private state.

Agents (`agents/`):

| Agent | Fate | Role |
|---|---|---|
| planner | new | hierarchical decomposition of a goal into a ticket tree (parent/blocked_by edges); never implements |
| implementer | reworked | pops one doable ticket, runs the pre-work gate, implements within declared scope, writes done-report with evidence |
| interface-auditor | new | audits one module boundary per mission: contracts, error paths, misuse cases; files tickets, never fixes |
| security-auditor | new (replaces auditor) | policy-driven sweep; every finding becomes a permanent policy rule plus a ticket |
| prover | new | turns `frob:invariant` anchors into property tests or policy rules; drives invariant evidence to 100% |
| reviewer | reworked | verifies a done-report against the actual diff and evidence before a ticket may close |
| debugger | kept | one failing test at a time; records failures as ticket failure-log entries |

Deleted agents: architect, oracle, orchestrator, refactorer, smart-start,
tester, integration-tester, system-tester (folded into implementer/prover
missions or obsolete with dispatch/mission gone).

Skills (`skills/`):

| Skill | Fate | Role |
|---|---|---|
| plan | reworked | goal -> ticket tree via planner; no more freestanding TODO.md workflow |
| next | new | pop doable ticket -> pre-work gate -> implement -> evidence -> done-report -> close |
| audit | new (replaces review + audit-fix) | interface-auditor + security-auditor sweep; output is tickets and policy rules, not prose |
| prove | new | run prover until `frob check` invariant gates pass |
| fix | kept | tight single-test loop, unchanged |
| document | reworked | driven by the drift report: fix exactly what `frob check` says is stale, then `frob ack` |

Deleted skills: develop, implement, write-tests, review (their jobs are now
next/audit/prove, all mediated by the queue so nothing is popped off the top
half of the stack and forgotten).

## Cross-cutting design decisions

- **Source of truth is tracked text; caches are derived.** Chosen over a
  SQLite source of truth because text merges, diffs, and reviews; the cache
  is rebuildable at any time. (Matches the local-first pattern that won in
  the 2026 code-intelligence market.)
- **Renames are re-link-on-failure.** A renamed symbol dangles its edges;
  the drift gate fails and suggests candidates by matching body digests. No
  stable IDs embedded in code -- rejected as annotation noise.
- **Absence is an error.** Coverage gates make missing declarations fail,
  so laziness has nowhere to hide except explicit `frob:waive` directives,
  which are themselves reported.
- **Result everywhere.** Every fallible operation returns typani
  `Result[T, E]` with a module ErrorSet; exceptions only for programmer
  bugs. CLI runners convert Results to exit codes and parseable output.
- **Gates must be fast or they will be skipped.** Incremental reindexing
  (per-file content hashes); warm `frob check` budget is sub-second on this
  repo, and the graph gates add at most low hundreds of milliseconds.
- **Version target**: the rework ships as 0.1.0.

## Phases

0. Alpha purge: delete stale commands, agents, skills, docs, tests.
1. `frob.lang`: tree-sitter core (Python, TypeScript, Rust, C, C++).
2. `frob.graph`: registry, digests, edges, DSL, cache, lock, ack, drift.
3. `frob.tickets`: queue, state machine, attachments, clipboard.
3.5. `frob.gitio` + `frob.testing`: touched-set cross-language testing.
4. `frob.gates` + `frob.policy` + invariants; extend `frob check`.
5. Agents/skills replacement set.
6. Docs/README refresh; release 0.1.0.
7. (0.2.0) `frob-core` Rust kernels + smart dup: region-granular semantic
   clone detection with DUP001/DUP002 gates (docs/modules/dup.md).
8. (0.2.0) `frob.fuzz`: enforced property fuzzing, Arbitrary protocol,
   FUZZ gates (docs/modules/fuzz.md).

Post-0.2.0: `frob serve` (MCP adapter).

See `tickets.md` (`frob ticket doable`) for the dispatchable queue.
