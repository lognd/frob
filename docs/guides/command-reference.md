# Command reference: verb groups and the full surface

Moved out of README.md (T-4131) to keep the README scannable; this page
carries the full detail the README only summarizes.

## The verb groups

`frob --help` groups its surface into seven verb collections; every member
also works as its own standalone top-level command (`frob check` and `frob
quality check` are the same command). This page follows the CLI's own
grouping -- if the two ever disagree, that is a drift bug in one of them.
Reach for a group's concept, skip it once you know you don't need it, and
follow its docs/ pointer when you do.

### explore -- navigation

Answers "where is this symbol and what touches it" without editing
anything. Reach for it when you're orienting in an unfamiliar area of the
tree, before Serena or your editor's own search is warmed up, or from a
non-interactive script that just wants text output.

| Verb | What / when |
|---|---|
| `frob map` | Recursive directory tree with file sizes and line counts -- get the shape of a package fast |
| `frob outline` | A file's structural skeleton: classes, functions, signatures, line numbers |
| `frob xref` | Where a symbol is defined and every file that references it |
| `frob explore docs-search` | Full-text search through `docs/` |

Depth: docs/modules/cli.md (Navigation commands section).

### quality -- correctness and hygiene gates

Answers "is the tree clean, and where specifically is it not." This is
the group you run before closing a ticket or opening a PR; each member
also runs standalone for a narrower question than the aggregate `check`.

| Verb | What / when |
|---|---|
| `frob check` | The aggregate gate: ruff, ty, cycle/dup/arch/bind/exports, and every enforcement gate -- the one command that says whether the tree is clean |
| `frob test` | Selects and runs tests for the touched set against a base ref (or `--all`) -- fast, targeted, after a change |
| `frob dup` | Detect duplicate/clone code segments before you copy-paste a third time |
| `frob arch` | Long functions, god classes, coupling -- structural smell, not correctness |
| `frob bind` | Verify binding declarations match source signatures |
| `frob cycle` | Detect import cycles in Python packages |
| `frob mutate` | Mutation testing: perturb a file, see which mutants survive -- the honest test-quality oracle |
| `frob perf` | Profile a command/test suite and inspect its heat-map |

Depth: docs/modules/gates.md.

### design -- the model frob checks the code against

Answers "what is the code supposed to look like," the design-knowledge
side of the obligation graph that `quality` checks the code against.
Reach for it when you're documenting intent, not fixing a violation.

| Verb | What / when |
|---|---|
| `frob sys` | strata design-model audit: model-vs-code conformance, threat/CWE/compliance/PII, deploy proofs |
| `frob registry` | Exhaustiveness drift-lock over `docs/design/registry/*.yaml` |
| `frob docs` | Extract docstrings from a file/symbol (`--overview`) |
| `frob graph` | Obligation graph: build the cache, query a symbol's edges, explain drift |
| `frob exports` | Generate a ready-to-paste `__init__.py` from all public symbols |

Depth: docs/design/ for the design-knowledge model itself, docs/modules/graph.md for the graph.

### ops -- release, fleet, and infra plumbing

Answers "how does this repo get built, shipped, and kept tidy" -- the
mechanical side of running frob-enabled repos day to day, none of it
about the obligation graph itself.

| Verb | What / when |
|---|---|
| `frob release` | Mechanical semver from the public-API graph, plus the release gate |
| `frob natives` | Build declared `[[native]]` crates via `maturin develop` |
| `frob doctor` | Native-extension availability and derived-state health -- first command after install |
| `frob clean` | Remove build/test/cache artifacts (tiered, dry-run by default) |
| `frob fleet` | Cross-repo status/gate rollup and ticket routing over a `fleet.toml` manifest |
| `frob deploy` | Compile a host manifest into idempotent install/status/uninstall bash |
| `frob scaffold` | Scaffold a new project from a registered template |
| `frob gitlog` | Summarize git history filtered by conventional commit type |
| `frob stats` | DORA-ish delivery measurement: queue health + commit cadence |

Depth: docs/guides/release.md, docs/modules/fleet.md, docs/modules/deploy.md.

### ticket -- the ticket queue

Answers "what work exists, whose is it, and is it done." A git-tracked
queue where deferred work is a directive bound into the code, not a note
someone has to remember to act on. Reach for it any time you start,
scope, or close a unit of work -- most sessions live here.

| Verb | What / when |
|---|---|
| `frob ticket new` / `list` / `show` / `doable` | File, browse, and pick the next unblocked ticket |
| `frob ticket start` / `work` | Move a ticket to in-progress and set up its worktree |
| `frob ticket scope` | Expand/reduce a ticket's declared file scope (also a write lease) |
| `frob ticket evidence` / `done-report` / `close` | Bind test evidence, write the Done report, close the ticket |
| `frob ticket land` | One command: merge, check, splice, close, commit a worktree onto the checkout |

Depth: docs/modules/tickets.md, docs/modules/tickets-lifecycle.md.

### vet -- dependency vetting

Answers "can I trust this dependency" before it lands in the lockfile:
capability scan, CVE fingerprints, supply-chain/typosquat/lifecycle-script
checks. Reach for it whenever you add or bump a dependency; skip it
otherwise.

Depth: docs/modules/vet.md.

### serve -- MCP stdio adapter

Answers "let an agent query frob's own state directly" -- doable tickets,
stale docs, scope/graph queries -- as read-only MCP tools over stdio.
Reach for it when wiring frob into an agent host rather than a shell.

Depth: docs/modules/serve.md.

## Full command reference

The full, drift-locked command table (every top-level command bound to
the live subcommand registry -- DOC005 fails `frob check` if a row here
goes stale) lives in a collapsible section near the end of README.md
rather than being duplicated here. Use `frob <verb> --help` for flags.
