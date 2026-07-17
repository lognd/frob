# frob

The enforcement layer for agentic development. frob makes it impossible for
work to silently not happen: an obligation graph tracks every symbol's
identity, a statically-checkable ticket queue tracks every unit of work, and
a set of gates turn unaccounted-for change -- or unaccounted-for absence of
change -- into a `frob check` failure.

Division of labor: your editor or Serena navigates and edits code, frob
accounts for it. frob owns durable cross-artifact claims (docs, tickets,
invariants, policy) and their enforcement.

Install: `uv tool install frob`. For editable dev install: `pip install -e .`

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

## Commands

### Enforcement

| Command | Description |
|---------|-------------|
| `frob graph` | Obligation graph: build the cache, query a symbol's edges, or explain drift (`why`) |
| `frob ack` | Acknowledge current digests for one or more symbol refs, updating `frob.lock` |
| `frob ticket` | The statically-checkable ticket queue: new/list/show/doable/start/attach/block/close/fail |
| `frob check` | Aggregate quality gate: ruff, ty, cycle/dup/arch/bind/exports, and the enforcement gates |
| `frob test` | Select and run tests for the touched set vs a base ref (or `--all`) |

### Analysis

| Command | Description |
|---------|-------------|
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

### Setup

| Command | Description |
|---------|-------------|
| `frob scaffold` | Scaffold a new project from a registered template |

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

See `docs/quickstart.md` for the full walkthrough with real command output, and
`docs/` for per-command references and module design docs.
