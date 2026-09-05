<p align="center">
  <img src="docs/assets/frob-banner.svg" alt="frob: a small green goblin in an aviator cap hunched over a crystal ball of glowing rune-code. The enforcement layer for agentic development." width="100%"/>
</p>

# frob

frob is the enforcement layer for agentic development: an obligation graph
tracks every symbol's identity, a statically-checkable ticket queue tracks
every unit of work, and a set of gates turn unaccounted-for change -- code
with no ticket, a doc that drifted, a test that vanished -- into a `frob
check` failure. Your editor or an agent's own tools navigate and edit code;
frob accounts for it.

```bash
uv tool install frob
```

<!-- frob:waive DOC004 reason="illustrative first-run example, output captured below in the README's own intro; not a claim tracked elsewhere" -->
```bash
frob doctor
```

```text
frob version: 0.530.0

  frob_core: available (version=unknown)
  strata_core: available (version=unknown)

all native extensions available
```

`frob doctor` is a good first command: it confirms the install and reports
whether the two native acceleration extensions (`frob-core`, `strata-core`)
are present. Both are default dependencies of a plain install; if either is
absent frob still runs, in pure-Python mode, and says so loudly rather than
degrading silently -- see docs/guides/install.md.

---

## The enforcement loop

```
annotate -> check -> fix-or-waive
```

1. **Annotate.** As you write code, bind it to a ticket and its tests with
   comment directives: `frob:ticket T-0042`, `frob:tests <symref>`,
   `frob:doc docs/x.md#anchor`, `frob:invariant INV-007`.
2. **Check.** `frob check` builds the obligation graph, joins it against the
   ticket queue, docs, and policy, and fails on anything undeclared: a
   changed symbol with no ticket, a public function with no test, a doc that
   drifted out of sync, a diff that strayed outside its ticket's scope.
3. **Fix or waive.** Either close the gap (write the test, update the doc,
   file the ticket) or waive it explicitly with a reason:
   `frob:waive RULE-ID reason="..."`. A waiver is visible debt, never
   silence -- it shows up in every report.

Every violation message embeds its own remedy command, so an agent acting on
`frob check` output never hits a dead end.

---

## Quickstart

```bash
frob graph build                                  # build the obligation graph cache
frob ticket new --title "Add multiply function" \
    --kind feature --scope "src/demo/calc.py"     # T-0001
frob ticket start T-0001                          # pre-work sweep, -> in-progress

# write code, bind it: `# frob:ticket T-0001` above the new symbol,
# `# frob:tests <symref>` above the test that covers it

frob check . --ticket T-0001                      # fails: undeclared change
# ... add the directives, write the test ...
frob check . --ticket T-0001                      # coverage/scope/drift clean

frob test --base main                             # run exactly the touched-set tests
frob ack src/demo/calc.py::multiply --facet sig    # acknowledge a described contract
frob ticket close T-0001                           # requires evidence + a Done report
```

See docs/guides/quickstart.md for the full walkthrough with real command
output, docs/guides/install.md for install/degrade details, and docs/ for
per-command references and module design docs.

---

## The verb groups

`frob --help` groups its surface into seven verb collections; every member
also works as its own standalone top-level command (`frob check` and `frob
quality check` are the same command). This README follows the CLI's own
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

---

## Full command reference

Every top-level command, statically bound to the live subcommand registry
(a subcommand added or removed here with no matching row fails `frob
check`). The seven grouped rows below (`explore`/`quality`/`design`/`ops`/
`ticket`/`vet`/`serve`) are the verb collections above; everything else
also works standalone. Use `frob <verb> --help` for flags, or
docs/modules/cli.md for the tier ledger behind the grouping.

| Command | Description |
|---|---|
| `frob ack` | Acknowledge current digests for one or more symbol refs |
| `frob agent` | Print/export the dispatched-agent guard env |
| `frob arch` | Arch analysis: long functions, god classes, coupling |
| `frob bind` | Verify binding declarations match source signatures |
| `frob check` | Aggregate quality gate: ruff, ty, cycle/dup/arch/bind/exports, and every enforcement gate |
| `frob claude` | Sync this repo's tracked Claude config to `~/.claude/` |
| `frob clean` | Remove build/test/cache artifacts (tiered, dry-run by default) |
| `frob coverage` | Refresh `coverage.xml` / the coverage stamp, touched-set incremental by default |
| `frob cycle` | Detect import cycles in Python packages |
| `frob debt` | List outstanding `frob:debt` entries |
| `frob deploy` | Compile a host manifest into idempotent install/status/uninstall bash |
| `frob deprecated` | List outstanding `frob:deprecated` entries |
| `frob design` | Group: `sys`/`registry`/`docs`/`graph`/`exports` -- see "design" above |
| `frob docs` | Extract docstrings or search `docs/` for a file/symbol |
| `frob doctor` | Verify native extensions and report derived-state health |
| `frob dup` | Detect duplicate/clone code segments |
| `frob explore` | Group: `map`/`outline`/`xref`/`docs-search` -- see "explore" above |
| `frob exports` | Generate a ready-to-paste `__init__.py` from public symbols |
| `frob fleet` | Cross-repo status/gate rollup and ticket routing over `fleet.toml` |
| `frob fmt` | Canonicalize `frob:` directive comment line-wrapping |
| `frob format` | `ruff check --fix` + `ruff format`, write mode |
| `frob gitlog` | Summarize git history filtered by conventional commit type |
| `frob graph` | Obligation graph: build the cache, query symbols, explain drift |
| `frob map` | Recursive directory tree with file sizes and line counts |
| `frob mutate` | Mutation testing: perturb a file, see which mutants survive |
| `frob narrative` | Migrate a `T-####` narrative comment block |
| `frob natives` | Build declared `[[native]]` crates via `maturin develop` |
| `frob ops` | Group: `release`/`natives`/`doctor`/`clean`/`fleet`/`deploy`/`scaffold`/`gitlog`/`stats` -- see "ops" above |
| `frob outline` | Structural skeleton of a file: classes, functions, signatures |
| `frob parse` | Parse tool output (pytest/ruff/ty/clang/junit) into a compact summary |
| `frob perf` | Profile a command/test suite and inspect its heat-map |
| `frob pool` | Ratchet-pool baseline management for warn-rule findings |
| `frob profile` | Development profile (rapid/standard/fortress) status and downgrade |
| `frob quality` | Group: `check`/`test`/`dup`/`arch`/`bind`/`cycle`/`mutate`/`perf` -- see "quality" above |
| `frob refactor` | Transactional symbol move/rename/split |
| `frob registry` | Exhaustiveness drift-lock over `docs/design/registry/*.yaml` |
| `frob release` | Mechanical semver from the public-API graph, plus the release gate |
| `frob scaffold` | Scaffold a new project from a registered template |
| `frob serve` | MCP stdio adapter exposing frob's enforcement queries as tools |
| `frob stats` | DORA-ish delivery measurement: queue health + commit cadence |
| `frob status` | Delta-first movement summary since the last stamped baseline |
| `frob sync-skills` | Bidirectionally sync `agents/`/`skills/` into `~/.claude/` |
| `frob sys` | strata design-model audit: model-vs-code conformance, threat/CWE/compliance/PII, deploy proofs |
| `frob test` | Select and run tests for the touched set against a base ref (or `--all`) |
| `frob ticket` | Group: the statically-checkable ticket queue -- see "ticket" above |
| `frob verify` | The unverified-window tracker: depth/age/quarantine status |
| `frob vet` | Group: dependency capability/CVE/supply-chain vetting -- see "vet" above |
| `frob worktree` | Manage dispatched-agent git worktrees |
| `frob xref` | Find where a symbol is defined and every file that references it |

---

## More

- docs/guides/install.md -- native extensions, the T-0133 degrade contract, editable dev installs
- docs/guides/quickstart.md -- the loop above with real command output
- docs/modules/cli.md -- the CLI regrouping history and per-command tier ledger
- docs/ -- per-command references and module design docs
- CHANGELOG.md -- what shipped, grouped by area
