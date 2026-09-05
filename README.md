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

## Verbs

The commands below are the spine of frob; each has its own `--help` and a
fuller writeup under `docs/`.

| Verb | What it does | Reach for it when |
|---|---|---|
| `frob check` | Runs the whole gate family: ruff, ty, cycle/dup/arch/exports, and every enforcement gate | You want the one command that says whether the tree is clean |
| `frob test` | Selects and runs tests for the touched set against a base ref (or `--all`) | You changed code and want exactly the tests that cover it, fast |
| `frob ticket` | The statically-checkable ticket queue: new/list/show/doable/start/close/... | You're starting, scoping, or closing a unit of work |
| `frob format` | `ruff check --fix` + `ruff format` in write mode | You want the tree auto-fixed before `frob check` |
| `frob coverage` | Refreshes `coverage.xml` / the coverage stamp, touched-set incremental by default | `frob check`'s coverage gate is stale or missing |
| `frob ack` | Acknowledges a symbol's current signature/body/doc digest | A described contract changed on purpose and the drift gate should stop flagging it |
| `frob vet` | Scans dependencies for capability, CVE, and supply-chain risk | You added or bumped a dependency |
| `frob doctor` | Reports native-extension availability and derived-state health | First command after install, or when something looks stale |
| `frob scaffold` | Scaffolds a new project from a registered template | You're starting a new frob-enabled repo |
| `frob serve` | MCP stdio adapter exposing doable tickets and drift queries as read-only tools | You want an agent to query frob's state directly |
| `frob release` | Mechanical semver from the public-API graph, plus the release gate | You're cutting a version |

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

## Full command reference

Every top-level command, statically bound to the live subcommand registry
(a subcommand added or removed here with no matching row fails `frob
check`).

### Enforcement

| Command | Description |
|---------|-------------|
| `frob graph` | Obligation graph: build the cache, query a symbol's edges, explain drift (`why`), or walk the transitive doc/code digest-drift closure (`affects`) |
| `frob design` | Design-knowledge verb group: `sys`/`registry`/`docs`/`graph`/`exports`; each also stays available as its own standalone command below |
| `frob ack` | Acknowledge current digests for one or more symbol refs, updating `frob.lock` |
| `frob ticket` | The statically-checkable ticket queue: new/list/show/doable/start/attach/block/close/fail |
| `frob check` | Aggregate quality gate: ruff, ty, cycle/dup/arch/bind/exports, and the enforcement gates |
| `frob quality` | Correctness/hygiene verb group: `check`/`test`/`dup`/`arch`/`bind`/`cycle`/`mutate`/`perf`; each also stays available as its own standalone command below |
| `frob test` | Select and run tests for the touched set vs a base ref (or `--all`) |
| `frob vet` | Dependency capability vetting: source-resolved capability scan, CVE fingerprints, supply-chain/obfuscation checks |
| `frob sys` | strata system-design audit: model-vs-code conformance, threat/CWE/compliance/PII, deploy proofs (`plan`/`doc`/`audit`/`export`) |
| `frob deploy` | Auditable OS-layer deployment: compile a host manifest into idempotent install/status/uninstall + VM audit |
| `frob ops` | Release/fleet/infra verb group: `release`/`natives`/`doctor`/`clean`/`fleet`/`deploy`/`scaffold`/`gitlog`/`stats`; each also stays available as its own standalone command below |
| `frob release` | Mechanical semver from the public-API graph and the release gate (`stamp`/`check`) |
| `frob registry` | Unified design-knowledge registry: exhaustiveness drift-lock over `docs/design/registry/*.yaml` (`audit`/`add`) |
| `frob pool` | Ratchet-pool baseline management: freeze warn-rule findings as a tracked baseline so new findings error (`snapshot`/`clear`) |
| `frob debt` | List outstanding `frob:debt` entries (rule, site, ticket, until) |
| `frob profile` | Show or explicitly downgrade the effective rapid/standard profile ratchet (`show`/`downgrade --reason`) |
| `frob claude` | Sync this repo's tracked Claude config (hooks, agent-playbook.md) to `~/.claude/` via `sync [--check]` |
| `frob sync-skills` | Bidirectionally sync this repo's `agents/`/`skills/` directories into `~/.claude/agents`/`~/.claude/skills` |
| `frob deprecated` | List outstanding `frob:deprecated` entries (symref, since, sunset, ticket, status) |
| `frob fleet` | Cross-repo status/gate rollup and ticket routing over a `fleet.toml` manifest of sibling repos (`status`/`route`) |

### Analysis

| Command | Description |
|---------|-------------|
| `frob explore` | Navigation verb group: `map`/`outline`/`xref`/`docs-search`; each also stays available as its own standalone command below |
| `frob map` | Recursive directory tree with file sizes and line counts |
| `frob outline` | Structural skeleton of a file: classes, functions, signatures, line numbers |
| `frob xref` | Find where a symbol is defined and every file that references it |
| `frob cycle` | Detect import cycles in Python packages |
| `frob dup` | Detect duplicate/clone code segments |
| `frob arch` | Arch analysis: long functions, god classes, coupling |
| `frob docs` | Extract docstrings or search `docs/` for a file/symbol |
| `frob exports` | Generate a ready-to-paste `__init__.py` from all public symbols |
| `frob bind` | Verify binding declarations match source signatures |
| `frob parse` | Parse tool output (pytest/ruff/ty/clang/junit) into a compact summary |
| `frob gitlog` | Summarize git history filtered by conventional commit type |
| `frob perf` | Profiling (`profile`/`heat`) and the linear-scan perf gates |
| `frob mutate` | Mutation testing: the honest test-quality oracle |
| `frob narrative` | Migrate a `T-####` narrative comment block |
| `frob refactor` | Transactional symbol move/rename/split |
| `frob stats` | DORA-ish delivery measurement (queue health + commit cadence); measurement only |
| `frob status` | Delta-first movement summary: findings healed/introduced since the last stamped baseline, verification lag, ticket landing velocity |
| `frob serve` | MCP stdio adapter exposing doable tickets, stale docs, scope/graph queries as read-only tools |

### Setup

| Command | Description |
|---------|-------------|
| `frob scaffold` | Scaffold a new project from a registered template |
| `frob doctor` | Verify native extensions (`frob_core`, `strata_core`) are installed and report derived-state health |
| `frob natives` | Build declared `[[native]]` crates via `maturin develop`, sharing one git-common-dir-keyed `CARGO_TARGET_DIR` (`build`) |
| `frob coverage` | Refresh coverage.xml / the coverage stamp (touched-set incremental by default, `--full` for a whole-suite run) |
| `frob verify` | The unverified-window tracker: depth/age/quarantine status, force a drain, explain an attribution, dispose a quarantined finding (`status`/`now`/`explain`/`dispose`) |
| `frob clean` | Remove build/test/cache artifacts (tiered, dry-run by default) |
| `frob fmt` | Canonicalize `frob:` directive comment line-wrapping: fewest physical lines within the line-length limit (`--check` previews without writing) |
| `frob format` | `ruff check --fix` + `ruff format`, write mode: all rules by default, or `--select I` (import sorting only) with `--select-imports-only` |
| `frob agent` | Print/export the dispatched-agent guard env (`FROB_WORKTREE`/`FROB_AGENT`) for a worktree (`env`) |
| `frob worktree` | Manage dispatched-agent git worktrees: lease-aware stale-worktree cleanup (`sweep`) |

---

## More

- docs/guides/install.md -- native extensions, the T-0133 degrade contract, editable dev installs
- docs/guides/quickstart.md -- the loop above with real command output
- docs/ -- per-command references and module design docs
- CHANGELOG.md -- what shipped, grouped by area
